package main

import (
	"bytes"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"
)

var group sync.WaitGroup

var statsHost string
var persistHost string

func Worker(stream <-chan json.RawMessage, errs chan<- error) {
	t := http.Transport(*http.DefaultTransport.(*http.Transport))
	t.MaxIdleConnsPerHost = 100
	c := &http.Client{
		Transport: &t,
		Timeout:   time.Duration(30) * time.Second,
	}
	defer group.Done()
	for record := range stream {
		resp, err := c.Post(statsHost, "application/json", bytes.NewReader(record))
		if err != nil {
			errs <- fmt.Errorf("error requesting service 1: %w", err)
			continue
		}
		readed, err := io.Copy(io.Discard, resp.Body)
		if err != nil {
			errs <- fmt.Errorf("error reading body: %w", err)
		}
		log.Println("response from service 1 has", readed, "bytes")
		resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			errs <- fmt.Errorf("non-ok response from service 1 (code %v)", resp.StatusCode)
			continue
		}
		resp, err = http.Post(persistHost, "application/json", resp.Body)
		if err != nil {
			errs <- fmt.Errorf("error requesting service 2: %w", err)
			continue
		}
		readed, err = io.Copy(io.Discard, resp.Body)
		if err != nil {
			errs <- fmt.Errorf("error reading body: %w", err)
		}
		log.Println("response from service 1 has", readed, "bytes")
		resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			errs <- fmt.Errorf("non-ok response from service 2 (code %v)", resp.StatusCode)
		}
	}
}

func main() {
	logFile, err := os.OpenFile("logs/feeder.log", os.O_CREATE|os.O_RDWR, 0666)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	defer logFile.Close()
	log.SetOutput(logFile)
	statsHost = os.Getenv("STATS_URL")
	if statsHost == "" {
		statsHost = "http://statistics:8080"
	}
	persistHost = os.Getenv("PERSIST_URL")
	if persistHost == "" {
		persistHost = "http://persister:8080"
	}
	file, err := os.Open(os.Getenv("FEEDER_DATASET"))
	if err != nil {
		log.Fatalln(err)
	}
	reader, err := gzip.NewReader(file)
	if err != nil {
		log.Fatalln(err)
	}
	workersCount := 32
	stream := make(chan json.RawMessage, workersCount)
	defer close(stream)
	errStream := make(chan error, workersCount)
	defer close(errStream)
	go func() {
		for v := range errStream {
			log.Println(v)
		}
	}()
	for i := 0; i < workersCount; i++ {
		log.Println("dispatching worker", i)
		group.Add(1)
		go Worker(stream, errStream)
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
		stream <- record
	}
	group.Wait()
}
