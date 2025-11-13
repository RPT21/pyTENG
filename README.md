# ⚡ pyTENG — Triboelectric Nanogenerator Measurement System

`pyTENG` is a Python-based project designed to control and automate the measurement system for **triboelectric devices** (TENGs — *Triboelectric Nanogenerators*).  

This software provides an interface for **data acquisition, visualization, and storage** of measurements obtained from triboelectric energy harvesting experiments.  

---

## 🎯 Main Features

- **Real-time data acquisition** from the measurement hardware using **PyDAQmx**.  
- **Live plotting and visualization** of electrical signals with **PyQtGraph**.  
- **User interface** built with **PyQt5** and **QtPy**, allowing easy control of experiments.  
- **Automatic data export** to Pickle (`.pkl`).  
- **Remote communication** and data transfer with **Paramiko** (SSH/SFTP) with a Raspberry Pi.  

---

## 🧠 Technical Overview

The project is fully developed in **Python 3.12+**, and designed for **Windows 10/11** systems with National Instruments DAQ hardware.  
It uses a modular architecture, separating components for data acquisition, signal processing, and visualization.

---

# 🐍 Setting up the Python Environment in PyCharm

This project already includes a `requirements.txt` file with all necessary dependencies.  
**PyCharm can automatically detect this file, create a virtual environment, and install all packages** — no manual setup required if configured properly.

---

## ⚙️ 1️⃣ Automatic detection and setup

When you open the project in PyCharm for the first time, it will:

1. Detect the `requirements.txt` file.  
2. Offer to **create a virtual environment** automatically.  
3. Ask if you want to **install dependencies from `requirements.txt`**.

You’ll see a message like:

> *“Requirements file detected. Create virtual environment and install dependencies?”*

✅ Click **Yes** (or **Install requirements**) and PyCharm will:
- Create a `.venv` folder inside your project.  
- Run:
  ```bash
  pip install -r requirements.txt
  

