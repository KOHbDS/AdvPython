#!/bin/bash

# Запуск тестов с измерением покрытия
python -m pytest --cov=app tests/ --cov-report=html --cov-report=term

# Вывод информации о покрытии
echo "Coverage report generated in htmlcov/ directory"
