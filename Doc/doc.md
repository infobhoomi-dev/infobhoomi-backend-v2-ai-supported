Microsoft Windows [Version 10.0.22631.3958]
(c) Microsoft Corporation. All rights reserved.

D:\Office\Django>python -m venv .

D:\Office\Django>python -m venv venv

D:\Office\Django>venv\Scripts\activate.bat

(venv) D:\Office\Django>pip install django
Collecting django
Using cached Django-5.0.7-py3-none-any.whl.metadata (4.1 kB)
Collecting asgiref<4,>=3.7.0 (from django)
Using cached asgiref-3.8.1-py3-none-any.whl.metadata (9.3 kB)
Collecting sqlparse>=0.3.1 (from django)
Downloading sqlparse-0.5.1-py3-none-any.whl.metadata (3.9 kB)
Collecting tzdata (from django)
Using cached tzdata-2024.1-py2.py3-none-any.whl.metadata (1.4 kB)
Using cached Django-5.0.7-py3-none-any.whl (8.2 MB)
Using cached asgiref-3.8.1-py3-none-any.whl (23 kB)
Downloading sqlparse-0.5.1-py3-none-any.whl (44 kB)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.2/44.2 kB 197.2 kB/s eta 0:00:00
Using cached tzdata-2024.1-py2.py3-none-any.whl (345 kB)
Installing collected packages: tzdata, sqlparse, asgiref, django
Successfully installed asgiref-3.8.1 django-5.0.7 sqlparse-0.5.1 tzdata-2024.1

[notice] A new release of pip is available: 24.0 -> 24.2
[notice] To update, run: python.exe -m pip install --upgrade pip

(venv) D:\Office\Django> python.exe -m pip install --upgrade pip
Requirement already satisfied: pip in d:\office\django\venv\lib\site-packages (24.0)
Collecting pip
Using cached pip-24.2-py3-none-any.whl.metadata (3.6 kB)
Using cached pip-24.2-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
Attempting uninstall: pip
Found existing installation: pip 24.0
Uninstalling pip-24.0:
Successfully uninstalled pip-24.0
Successfully installed pip-24.2

(venv) D:\Office\Django> python.exe -m pip install --upgrade pip
Requirement already satisfied: pip in d:\office\django\venv\lib\site-packages (24.2)

(venv) D:\Office\Django>pip install djangorestframework
Collecting djangorestframework
Using cached djangorestframework-3.15.2-py3-none-any.whl.metadata (10 kB)
Requirement already satisfied: django>=4.2 in d:\office\django\venv\lib\site-packages (from djangorestframework) (5.0.7)
Requirement already satisfied: asgiref<4,>=3.7.0 in d:\office\django\venv\lib\site-packages (from django>=4.2->djangorestframework) (3.8.1)
Requirement already satisfied: sqlparse>=0.3.1 in d:\office\django\venv\lib\site-packages (from django>=4.2->djangorestframework) (0.5.1)
Requirement already satisfied: tzdata in d:\office\django\venv\lib\site-packages (from django>=4.2->djangorestframework) (2024.1)
Using cached djangorestframework-3.15.2-py3-none-any.whl (1.1 MB)
Installing collected packages: djangorestframework
Successfully installed djangorestframework-3.15.2

(venv) D:\Office\Django>pip install --upgrade pip setuptools wheel
Requirement already satisfied: pip in d:\office\django\venv\lib\site-packages (24.2)
Requirement already satisfied: setuptools in d:\office\django\venv\lib\site-packages (65.5.0)
Collecting setuptools
Using cached setuptools-72.1.0-py3-none-any.whl.metadata (6.6 kB)
Collecting wheel
Using cached wheel-0.43.0-py3-none-any.whl.metadata (2.2 kB)
Using cached setuptools-72.1.0-py3-none-any.whl (2.3 MB)
Using cached wheel-0.43.0-py3-none-any.whl (65 kB)
Installing collected packages: wheel, setuptools
Attempting uninstall: setuptools
Found existing installation: setuptools 65.5.0
Uninstalling setuptools-65.5.0:
Successfully uninstalled setuptools-65.5.0
Successfully installed setuptools-72.1.0 wheel-0.43.0

(venv) D:\Office\Django>pip install C:/geo/GDAL-3.4.3-cp311-cp311-win_amd64.whl
Processing c:\geo\gdal-3.4.3-cp311-cp311-win_amd64.whl
Installing collected packages: GDAL
Successfully installed GDAL-3.4.3

(venv) D:\Office\Django>python manage.py runserver
