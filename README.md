ike
===

### Installation

Clone the project with git.

    git clone git@github.com:blandry/ike.git
    
Setup yourself a virtual environment.

    python utils/virtualenv.py env
    
Start your environement and install the project's requirements (you will have to activate your environement every time you run the project).

    . env/bin/activate
    pip install -r requirements.txt
    
Create yourself a test database.

    python syncdb.py
    
Optionally you can load the lodging data in your database. This may take a while, there are 50 000 hotels to be loaded by default.

    python loadhotels.py
    
Start the project's server

    python application.py
