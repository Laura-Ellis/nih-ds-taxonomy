# Project Setup – Windows (No Anaconda)

This project uses a local virtual environment (`.venv`) and a simple task runner (`tasks.py`).

# TL;DR:
#### Create virtual environment
```python tasks.py create-venv```
#### Activate (PowerShell)
```.venv\Scripts\Activate```
#### Install dependencies
```python tasks.py install```
#### Launch Jupyter
```python tasks.py jupyter```
#### Update dependencies
```python tasks.py freeze```
#### push to GitHub (after initial commit)
```git remote add origin https://github.com/Laura-Ellis/nih-ds-taxonomy.git
git branch -M main
git push -u origin main
```
#### Recreate environment
```cd nih-ds-taxonomy
python tasks.py create-venv
python tasks.py install
python tasks.py jupyter```
```
---
# Full version

## 1. Requirements

- Windows
- Python 3.10+ on PATH (`python --version`)
- Git 

---

## 2. Folder Structure

```text
nih-ds-taxonomy/
  data/
    raw/
    processed/
  notebooks/
  src/
  reports/
  config/
  tasks.py
  requirements.txt        (you create from requirements.template.txt)
  requirements.template.txt
  PROJECT_SETUP.md
  README.md
```

## 3. First-time environment setup (from project root)
```python tasks.py create-venv```

### Create requirements.text (see template)

## 4. Launch jupyter
```jupyter notebook```

## 5. Update dependencies
```python tasks.py freeze```

## 6. Github
```git remote add origin https://github.com/Laura-Ellis/nih-ds-taxonomy.git
git branch -M main
git push -u origin main
```

## 7. to Recreate environment
```cd nih-ds-taxonomy
python tasks.py create-venv
python tasks.py install
python tasks.py jupyter
```





