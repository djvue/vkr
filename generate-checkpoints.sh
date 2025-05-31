#!/bin/bash

for number in 100 200 300 400 500 600 700 800 900 1000 1100 1200 1300 1400 1500
do
    echo "starting generate checkpoint $number"
    python eval.py generate checkpoints_model_12/checkpoint-$number 300 --no-fixing
    echo "finished generate checkpoint $number"
    echo ""
done
