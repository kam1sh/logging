package main

import (
	"bytes"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/schollz/progressbar/v3"
)

var group sync.WaitGroup

var statsHost string
var persistHost string

func Worker(stream <-chan json.RawMessage) {
	c := &http.Client{
		Transport: &http.Transport{
			MaxIdleConnsPerHost: 100,
		},
		Timeout: time.Duration(30) * time.Second,
	}
	svcs := map[string]string{
		"statistics": statsHost,
		"storage":    persistHost,
	}
	defer group.Done()
	for record := range stream {
		for name, addr := range svcs {
			resp, err := c.Post(addr, "application/json", bytes.NewReader(record))
			if err != nil {
				log.Error().
					AnErr("error", err).
					Str("destination", name).
					Msg("error requesting service")
				continue
			}
			readed, err := io.Copy(io.Discard, resp.Body)
			if err != nil {
				log.Error().
					AnErr("error", err).
					Str("destination", name).
					Msg("error reading body")
			}
			log.Info().
				Str("destination", name).
				Int64("bytes", readed).
				Msg("response readed")
			resp.Body.Close()
			if resp.StatusCode != http.StatusOK {
				log.Error().
					Str("destination", name).
					Int("code", resp.StatusCode).
					Msg("non-ok response from service")
				continue
			}
		}
	}
}

func main() {
	logFile, err := os.OpenFile("logs/feeder.json", os.O_CREATE|os.O_RDWR, 0666)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	defer logFile.Close()
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMs
	log.Logger = log.Output(logFile)
	statsHost = os.Getenv("STATS_URL")
	if statsHost == "" {
		statsHost = "http://statistics:8080"
	}
	persistHost = os.Getenv("PERSIST_URL")
	if persistHost == "" {
		persistHost = "http://persister:8080"
	}
	limit := os.Getenv("FEEDER_LIMIT")
	if limit == "" {
		limit = "103928340" // total records in the dump
	}
	limitNum, err := strconv.ParseInt(limit, 10, 32)
	if err != nil {
		log.Fatal().
			AnErr("error", err).
			Msg("error parsing row limit")
	}
	bar := progressbar.Default(limitNum)
	file, err := os.Open(os.Getenv("FEEDER_DATASET"))
	if err != nil {
		log.Fatal().
			AnErr("error", err).
			Msg("error while opening dataset")
	}
	reader, err := gzip.NewReader(file)
	if err != nil {
		log.Fatal().
			AnErr("error", err).
			Msg("error reading dataset gzip header")
	}
	workersCount := 2
	stream := make(chan json.RawMessage, workersCount)
	for i := 0; i < workersCount; i++ {
		log.Info().
			Int("worker", i).
			Msg("dispatching worker")
		group.Add(1)
		go Worker(stream)
	}
	decoder := json.NewDecoder(reader)
	if _, err := decoder.Token(); err != nil {
		log.Fatal().
			AnErr("error", err).
			Msg("error parsing first json token")
	}
	for i := 0; i < int(limitNum); i++ {
		bar.Add(1)
		var record json.RawMessage
		err = decoder.Decode(&record)
		if err != nil {
			log.Error().
				AnErr("error", err).
				Msg("error parsing json")
			continue
		}
		stream <- record
	}
	close(stream)
	group.Wait()
}
