# Better-UO-Scheduler

## Link

https://quackademics.me


## Local Host Set Up if not using the link above


## Frontend Setup
Change Directory
~~~
cd frontend
~~~

Install dependencies and run
~~~
npm install
npm run dev
~~~

## Backend Setup
Change Directory to backend directory
~~~
cd backend
~~~

Create virtual env
~~~
python3 -m venv venv
source venv/bin/activate
~~~

Installl Requirements
~~~
pip install -r requirements.txt
~~~

Run
~~~
uvicorn app:app --reload
~~~

## Getting it on your browser
Copy the local host link that appeared after "npm run dev" and paste it into your browser and give it a minute or 2 to load the data. After running the backend once you see "INFO: Application startup complete." you can click the link and start using the website locally.


