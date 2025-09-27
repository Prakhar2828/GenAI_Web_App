database being used: (not sure about access for multiple users right now)
psql -U postgres -d traffic_simulation_db
Before using you need to download the LLM software:
Download llama2 software

Also make sure to redownload dependencies from requirements.txt, I added some

####################################
STEPS FOR STARTING PROGRAM:
####################################

ALL OF THESE STEPS MUST BE DONE ON SEPARATE TERMINALS
THERE SHOULD BE 3 TERMINALS BEING USED

1.)
In first terminal start Llama2 LLM using:
ollama run llama2 (This is gonna cause an issue if you haven't created an instance yet.
I honestly forget what command you need to run first, but you only need to run it once to create a Llama2 instance that you can use from this point on. Just run "ollama run llama2" and paste the error in ChatGPT and it'll explain how to fix it. If you do this please paste those steps into here.)

2.)
In second terminal:
Running backend:
cd into backend 
venv\Scripts\activate
If bash:
$ source venv/Scripts/activate

Then do:
flask run

3.)
In third terminal:

Running frontend:
cd into frontend
npm start

GUI login page:
username: admin
password: password

Now you can use the LLM chatbot and it should know what you're talking about when referencing the sample files. If you want more accurate answers reference the file by name.

Docker steps:
1. docker build -t cs4624-all-in-one . (copy paste this into the terminal)

2. docker stop cs4624-all-in-one (copy paste this into the terminal)

3. docker rm cs4624-all-in-one (copy paste this into the terminal)

4. docker run -d ` (copy paste this into the terminal)
 --name cs4624-all-in-one `
 -p 5000:5000 `
 -p 11434:11434 `
 cs4624-all-in-one

 (copy paste the above line by line after 4.)

5. docker ps (Copy paste this into the terminal)

6. docker logs -f cs4624-all-in-one (copy paste this into terminal)# GenAI_Web_App
