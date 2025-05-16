# Обучение модели для генерации юнит тестов на языке golang

## Описание

Код логически разделен на 3 части:
1. dataset (dataset/*) - подготовка датасета
2. scoring (scoring/*) - код, выполняющий скоринг/оценку качества юнит теста
3. training (./train.py) - код для обучения модели
4. evaluating (./eval.py, ./eval_analyzer.ipynb) - код, проверяющий качество обученной модели и сравнение с исходной моделью

### Dataset

Можно смотреть описание по шагам в `dataset/dataset.ipynb`

Датасет создан на основе `bigcode/the-stack-v2-dedup`, который использовался в качестве подготовленного списка дедуплицированных файлов в публичных репозиториях github.com

Репозитории скачаны в виде архивов напрямую из github

Содержимое репозиториев было проанализировано и проекты, файлы с кодом были отфильтрованы по возможности написания тестов.
Так были исключены проекты
- без системы модулей (go.mod)
- с невалидными или приватными модулями, без зависимостей не получится запустить тесты
- файлы тестов, потому что для выбранного подхода они не нужны. Только код на который будут писаться тесты
- генерированные файлы, они спицифичны, на них обычно не пишут тесты, и они негативно влияют на качество модели
- файлы без функций, кроме main(). Main можно протестировать только интеграционным тестом, которые сложны в реализации и сетапе для запуска
- файлы с build тегами, так как для запуска требуется использовать определенные параметры, и может потребоваться определенная архитектура процессора
- пакеты в репозитории с синтаксическими ошибками, невалидным кодом на go

Файлы с кодом анализируются, для каждой функции создается своя запись в датасете

Промпт создается по такому принципу:
- system_message с контекстом по задаче
- user сообщение со сгенерированным кодом:
  - код тестируемой функция
  - все зависимости функции: импорты, глобальные переменные, другие функции, константы; все зависимости зависимостей и т.д.
  - зависимости в промпт добавляются до тех пор, пока промпт не превысит ограничение на длину, остальные зависимости игнорируются
- в user сообщении также указана функция, которую нужно протестировать

### Scoring server

Логика скорера:
- сохраняет тест в нужный пакет
- форматирует импорты утилитой goimports (увеличиваем число рабочих тестов для модели)
- повторно проверяет и скачивает зависимости (так как теперь появились зависимости в тестовом файле)
- запускает сам тест с записью метрик покрытия по функциям
- анализируем покрытие кода
- подчищаем за собой
- рассчитываем reward по логике

    - 0 if test contains errors and not runnable:
        - failed to get deps
        - failed to format imports
        - test build failed (couldn't run tests, but failed tests are ok)

    - 0.5 for runnable test
    - 0.25 for success test
    - 0.05 for all success tests
    - 0.2 for coverage

Также написан сервер и клиент скорера, которые позволяют перенести работу с GPU на другой сервер, а скорер остается на более доступной машинке, также перенос сотен ГБ с кодом - это долгий и дорогой процесс

Для запуска scoring server можно использовать команду:
```bash
fastapi run scoring/scoring_server.py
```

### Training

Базовая модель `deepseek-ai/deepseek-coder-1.3b-instruct` обучена методом Group Relative Policy Optimization ([GRPO](https://huggingface.co/docs/trl/main/grpo_trainer))

Для запуска обучения модели можно использовать команду:
```bash
python train.py original model_12 3000 0 --resume
```

Описание аргументов
```bash
usage:
python train.py {source_model} {target_model} {take} {skip} [--resume]
source_model - original for original deepseek model, or ./data/{model_name} local model path
target_model - ./data/{model_name} local path to save trained model
take - train dataset size
skip - how much to skip at the beginning of the dataset
--resume - resume training from checkpoint
```

Параметры обучения можно смотреть в [исходниках train.py](./train.py)

### Evaluating

Для запуска проверки модели:
```bash
python eval.py generate model_12 500
```
В другой консоли
```bash
python eval.py score model_12 500
```

Описание аргументов
```bash
usage:
python eval.py {command} {model_name} {take}
command - score|generate - action, expected to run to processes score & generate in parallel
model_name - original for original deepseek model, or ./data/{model_name} local model path
take - eval size
```

Результаты пишутся в логи `logs/{model_name}/{generate,generate_fixed,score,score_fixed}.log`

Далее можно прогнать ячейки jupiter notebook `eval_analyzer.ipynb`

### Экспериментальный функционал

Некоторые эксперименты по изменению датасета, скоринга и обучения/проверки модели находятся в `exp/*`

## Результаты

На момент написания

Полученные метрики:
baseline reward -  `0.0815`
trained reward - `0.0944`
trained/baseline reward - `1.16` (+16% улучшение качества модели)