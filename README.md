# Обучение модели для генерации юнит тестов на языке golang

Код логически разделен на 3 части:
1. dataset (dataset/*) - подготовка датасета
2. scoring (scoring/*) - код, выполняющий скоринг/оценку качества юнит теста
3. training (./train.py) - код для обучения модели
4. evaluating (./eval.py, ./eval_analyzer.ipynb) - код, проверяющий качество обученной модели и сравнение с исходной моделью

### Dataset

Можно смотреть описание по шагам в `dataset/dataset.ipynb`

### Scoring server

Для запуска scoring server можно использовать команду:
```bash
fastapi run scoring/scoring_server.py
```

### Training

Для запуска обучения модели можно использовать команду:
```bash
python train.py
```

### Evaluating

Для запуска проверки модели:
```bash
python eval.py
```
Результаты запишутся в логи `logs/eval*.log`

Далее можно прогнать ячейки jupiter notebook `eval_analyzer.ipynb`

### Экспериментальный функционал

Некоторые эксперименты по изменению датасета, скоринга и обучения/проверки модели находятся в `exp/*`