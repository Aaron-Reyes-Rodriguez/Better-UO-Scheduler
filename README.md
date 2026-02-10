# Better-UO-Scheduler

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