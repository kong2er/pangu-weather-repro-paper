#!/usr/bin/env bash
set -e

MODEL_DIR=/root/autodl-tmp/pangu-weather-repro/models
mkdir -p $MODEL_DIR
cd $MODEL_DIR

base=https://huggingface.co/OpenEarthLab/Pangu-Weather/resolve/main

wget -c $base/pangu_weather_1.onnx
wget -c $base/pangu_weather_3.onnx
wget -c $base/pangu_weather_6.onnx
wget -c $base/pangu_weather_24.onnx

echo "✅ models downloaded"
ls -lh
