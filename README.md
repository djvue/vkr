# Обучение модели для генерации юнит тестов на языке golang

## Описание

Код логически разделен на 3 части:
1. dataset (dataset/*) - подготовка датасета
2. scoring (scoring/*) - код, выполняющий скоринг/оценку качества юнит теста
3. training (./train.py) - код для обучения модели
4. evaluating (./eval.py, ./eval_analyzer.ipynb) - код, проверяющий качество обученной модели и сравнение с исходной моделью

### Dataset - Подготовка датасета

Можно смотреть описание по шагам в `dataset/dataset_0.ipynb`,  `dataset/dataset_1.ipynb`,  `dataset/dataset_2.ipynb`.

1. [dataset/dataset_0.ipynb](./dataset/dataset_0.ipynb) - 1 часть, скачивание и фильтрация файлов

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

2. [dataset/dataset_1.ipynb](./dataset/dataset_1.ipynb) - 2 часть, генерация по файлам

Тестируем генерацию completion-ов моделью, скорим результат

Видим малое количество успешных тестов, низкое покрытие, ниже ожидаемого. Проблема в слишком большом среднем размере файла. Файлы содержат множество функций, но модель генерирует тесты для 1-2 функций. Также количество ошибок увеличивается и качество сгенерированного кода ухудшается из-за слишком большого входного контекста, в части кейсов он обрезается, и отсутствия необходимых зависимостей для генерации корректного кода, который находится в других файлах пакета или проекта.

Принимаем решение пересобрать датасет с примерами по функциям.

3. [dataset/dataset_2.ipynb](./dataset/dataset_2.ipynb) - 3 часть, генерация по функциям

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
- запускаем расчет mutation_score
- подчищаем за собой
- рассчитываем reward по логике

    - 0 if test contains errors and not runnable:
        - failed to get deps
        - failed to format imports
        - test build failed (couldn't run tests, but failed tests are ok)

    - 0.45 for runnable test
    - 0.0...0.25 for success test
    - 0.0...0.2 for coverage
    - 0.0...0.1 for mutation score

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

Полученные метрики

|                                    |   no fixing iteration |   with fixing iteration |
|:-----------------------------------|----------------------:|------------------------:|
| count                              |              500      |                500      |
| original reward                    |                0.1562 |                  0.1585 |
| trained reward                     |                0.1818 |                  0.1853 |
| trained/original                   |                1.1639 |                  1.1688 |
| reward uplift, %                   |               16.39   |                 16.88   |
| original coverage                  |               15.0548 |                 15.0548 |
| trained coverage                   |               18.3006 |                 18.3006 |
| trained/original coverage          |                1.2156 |                  1.2156 |
| coverage uplift, %                 |               21.56   |                 21.56   |
| original no error coverage         |               79.7879 |                 79.7879 |
| trained no error coverage          |               83.0243 |                 83.0243 |
| trained/original no error coverage |                1.0406 |                  1.0406 |
| coverage no error uplift, %        |                4.06   |                  4.06   |
| original mutual                    |                0.0277 |                  0.0277 |
| trained mutual                     |                0.034  |                  0.034  |
| trained/original mutual            |                1.2276 |                  1.2276 |
| mutual uplift, %                   |               22.76   |                 22.76   |
| original all passed mutual         |                0.3548 |                  0.3548 |
| trained all passed mutual          |                0.3539 |                  0.3539 |
| trained/original all passed mutual |                0.9975 |                  0.9975 |
| mutual all passed uplift, %        |               -0.25   |                 -0.25   |
| original all passed                |                7.8    |                  7.8    |
| trained all passed                 |                9.6    |                  9.6    |
| trained/original all passed        |                1.2308 |                  1.2308 |
| all passed uplift, %               |               23.08   |                 23.08   |

В качестве скора для оценки модели выбрана средняя награда оценщика из раздела "Scoring"

- no fixing iteration - результаты оценки сгенерированного тест-файла модели
- with fixing-iteration - результаты оценки после 1 итерации исправления моделью ошибок, полученных оценщиком при попытке запустить (только для кейсов с ошибками)