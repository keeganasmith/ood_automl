# Description
This code base is intended for the development of an OOD interactive application that allows for easy access to Autogluon in an HPC environment.  

# Local Installation
## Requirements
- Python 3.10.X
- Node 22.12  
This application can be run locally: 
```
git clone https://github.com/keeganasmith/ood_automl.git
cd ood_automl
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```
open a new terminal and run the frontend:  
```
cd ood_automl/frontend/run-client
npm install
npm run dev
```
you should be able to view the interface at http://localhost:5173/
# Developers
File structure:  
- /backend: contains files related to the backend websockets, all of this code runs on the server (compute nodes)
- /backend/sample_datasets: contains some small sample datasets for testing application
- /backend/app.py: entry point for the server-side code. Contains the websockets for running autogluon and pre-processing datasets
- /backend/autogluon_log_parser.py: contains helper functions, for instance loading data from a file
- /backend/sessions.py: contains the main controllers for the websockets. This is the heart of the backend
- /frontend/run-client/src/App.vue: Currently contains all of the code for the frontend (will change)
# Contributing
Contributions are more than welcome, please create an issue for your proposed feature / bug fix, fork the repo, and make a pull request when finished.
