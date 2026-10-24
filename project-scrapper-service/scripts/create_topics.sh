#!/bin/bash

docker exec kafka-1 kafka-topics.sh \
  --create \
  --bootstrap-server localhost:9092 \
  --topic link-updates \
  --partitions 3 \
  --replication-factor 3 \
  --config min.insync.replicas=2 \
  --config retention.ms=86400000 \
  --config cleanup.policy=delete

echo "Topic link-updates created"