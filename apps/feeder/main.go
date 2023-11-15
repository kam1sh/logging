package main

import (
	"bytes"
	"compress/gzip"
	"context"
	"encoding/json"
	"fmt"
	"golang.org/x/time/rate"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
	"go.opentelemetry.io/otel/trace"
)

var group sync.WaitGroup

var statsHost string
var persistHost string

var tracer trace.Tracer

func Worker(ctx context.Context, stream <-chan json.RawMessage) {
	c := &http.Client{
		Transport: otelhttp.NewTransport(http.DefaultTransport),
		Timeout:   time.Duration(30) * time.Second,
	}
	defer group.Done()
	for record := range stream {
		ctx, span := tracer.Start(ctx, "record")
		hosts := map[string]string{
			"statistics": statsHost,
			"storage":    persistHost,
		}
		for name, url := range hosts {
			ctx, hostSpan := tracer.Start(ctx, "request", trace.WithAttributes(
				attribute.String("service", name),
			))
			req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(record))
			if err != nil {
				hostSpan.End()
				continue
			}
			req.Header.Add("content-type", "application/json")
			resp, err := c.Do(req)
			if err != nil {
				hostSpan.End()
				continue
			}
			readed, _ := io.Copy(io.Discard, resp.Body)
			span.SetAttributes(attribute.Int64("response.size", readed))
			resp.Body.Close()
			span.SetAttributes(attribute.Int("response.code", resp.StatusCode))
			hostSpan.End()
		}
		span.End()
	}
}

func initProvider() (func(context.Context) error, error) {
	ctx := context.Background()

	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName("feeder"),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	ctx, cancel := context.WithTimeout(ctx, time.Second)
	defer cancel()
	traceExporter, err := otlptracehttp.New(ctx,
		otlptracehttp.WithEndpoint("tempo:4318"),
		otlptracehttp.WithInsecure(),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create trace exporter: %w", err)
	}

	// Register the trace exporter with a TracerProvider, using a batch
	// span processor to aggregate spans before export.
	bsp := sdktrace.NewBatchSpanProcessor(traceExporter)
	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithResource(res),
		sdktrace.WithSpanProcessor(bsp),
	)
	otel.SetTracerProvider(tracerProvider)

	// set global propagator to tracecontext (the default is no-op).
	otel.SetTextMapPropagator(propagation.TraceContext{})

	// Shutdown will flush any remaining spans and shut down the exporter.
	return tracerProvider.Shutdown, nil
}

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()
	shutdown, err := initProvider()
	if err != nil {
		log.Fatalln(err)
	}
	defer func() {
		if err := shutdown(ctx); err != nil {
			log.Fatal("failed to shutdown TracerProvider: %w", err)
		}
	}()

	tracer = otel.Tracer("feeder/main")

	statsHost = os.Getenv("STATS_URL")
	if statsHost == "" {
		statsHost = "http://statistics:8080"
	}
	persistHost = os.Getenv("PERSIST_URL")
	if persistHost == "" {
		persistHost = "http://persister:8080"
	}
	http.DefaultTransport.(*http.Transport).MaxIdleConnsPerHost = 110
	file, err := os.Open(os.Getenv("FEEDER_DATASET"))
	if err != nil {
		log.Fatalln(err)
	}
	reader, err := gzip.NewReader(file)
	if err != nil {
		log.Fatalln(err)
	}
	workersCount := 4
	limiter := rate.Sometimes{First: 100 * workersCount, Interval: time.Second}
	stream := make(chan json.RawMessage, workersCount)
	defer close(stream)
	for i := 0; i < workersCount; i++ {
		log.Println("dispatching worker", i)
		group.Add(1)
		go Worker(ctx, stream)
	}
	limit := os.Getenv("FEEDER_LIMIT")
	if limit == "" {
		limit = "103928340" // total records in the dump
	}
	limitNum, err := strconv.ParseInt(limit, 10, 32)
	if err != nil {
		log.Fatalln(err)
	}
	decoder := json.NewDecoder(reader)
	if _, err := decoder.Token(); err != nil {
		log.Fatalln(err)
	}
	for i := 0; i < int(limitNum); i++ {
		var record json.RawMessage
		err = decoder.Decode(&record)
		if err != nil {
			log.Fatalln(err)
		}
		limiter.Do(func() {
			stream <- record
		})
	}
	group.Wait()
}
