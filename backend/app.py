from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, os, re, json, hashlib, jwt, datetime, pdfplumber
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='../frontend/static', template_folder='../frontend/templates')
CORS(app, supports_credentials=True)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, 'skillsync.db')
UPLOAD_DIR = os.path.join(BASE_DIR, '..', 'frontend', 'static', 'uploads')
SECRET_KEY = 'skillsync_secret_2024'
ALLOWED_EXT = {'pdf', 'txt'}

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── DB ──────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            email     TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            dept      TEXT,
            theme     TEXT DEFAULT 'light',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS applications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            company     TEXT NOT NULL,
            role        TEXT NOT NULL,
            interview_date TEXT NOT NULL,
            raw_text    TEXT,
            matched_skills TEXT,
            found_skills   TEXT,
            match_pct   INTEGER DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS skill_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id       INTEGER NOT NULL,
            skill_name   TEXT NOT NULL,
            done         INTEGER DEFAULT 0,
            deadline     TEXT,
            completed_at DATETIME,
            FOREIGN KEY (app_id) REFERENCES applications(id)
        );
        CREATE TABLE IF NOT EXISTS quiz_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            q_index    INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        ''')

init_db()

# ── AUTH HELPERS ─────────────────────────────────────────────────────────────
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def make_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization','').replace('Bearer ','')
        if not token:
            return jsonify({'error':'Token missing'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user_id = data['user_id']
        except:
            return jsonify({'error':'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

# ── SKILL DATA ────────────────────────────────────────────────────────────────
ROLE_SKILLS = {
    'Software Developer':        ['python','java','javascript','sql','git','rest api','linux','oop','data structures','algorithms','html','css'],
    'Data Scientist':            ['python','r','machine learning','tensorflow','pandas','numpy','sql','statistics','data visualization','scikit-learn','deep learning'],
    'Machine Learning Engineer': ['python','tensorflow','pytorch','scikit-learn','deep learning','nlp','docker','kubernetes','mlops','sql','algorithms'],
    'Full Stack Developer':      ['html','css','javascript','react','node.js','mongodb','sql','git','rest api','typescript','docker','express'],
    'DevOps Engineer':           ['linux','docker','kubernetes','jenkins','aws','ci/cd','terraform','ansible','bash','python','monitoring','git'],
    'Business Analyst':          ['sql','excel','power bi','tableau','agile','scrum','requirements gathering','data analysis','communication','jira','statistics'],
    'Cloud Architect':           ['aws','azure','gcp','kubernetes','docker','terraform','networking','security','microservices','python','iam','devops'],
}

ALL_SKILLS = [
    'python','java','javascript','typescript','c++','c#','r','go','kotlin','scala','rust','php','ruby','swift',
    'html','css','react','angular','vue','next.js','node.js','express','django','flask','spring','fastapi','redux','graphql',
    'sql','mysql','postgresql','mongodb','redis','cassandra','firebase','sqlite','nosql',
    'machine learning','deep learning','nlp','natural language processing','computer vision',
    'tensorflow','pytorch','keras','scikit-learn','opencv',
    'pandas','numpy','matplotlib','scipy','jupyter',
    'docker','kubernetes','jenkins','ansible','terraform','ci/cd','git','linux','bash','shell',
    'aws','azure','gcp','serverless','microservices','rest api','soap',
    'data science','data analysis','data visualization','tableau','power bi','excel','statistics','probability',
    'spark','kafka','airflow','big data','etl','data pipelines','mlops',
    'agile','scrum','jira','oop','algorithms','data structures','networking','security','iam','monitoring','devops',
    'communication','teamwork','leadership','problem solving','requirements gathering','business analysis',
]

VIDEOS = {
    'python':[{'t':'Python for Beginners – Full Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=rfscVS0vtbw'},{'t':'Python Full Course','ch':'Programming with Mosh','u':'https://www.youtube.com/watch?v=_uQrJ0TkZlc'}],
    'java':[{'t':'Java Tutorial for Beginners','ch':'Programming with Mosh','u':'https://www.youtube.com/watch?v=eIrMbAQSU34'},{'t':'Java Full Course','ch':'Telusko','u':'https://www.youtube.com/watch?v=BGTx91t8q50'}],
    'javascript':[{'t':'JavaScript Full Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=PkZNo7MFNFg'},{'t':'JavaScript Tutorial','ch':'Programming with Mosh','u':'https://www.youtube.com/watch?v=W6NZfCO5SIk'}],
    'sql':[{'t':'SQL Tutorial – Full Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=HXV3zeQKqGY'},{'t':'MySQL for Beginners','ch':'Programming with Mosh','u':'https://www.youtube.com/watch?v=7S_tz1z_5bA'}],
    'machine learning':[{'t':'ML Full Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=NWONeJKn6kc'},{'t':'ML for Everybody','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=i_LwzRVP7bg'}],
    'deep learning':[{'t':'Deep Learning Crash Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=VyWAvY2CF9c'},{'t':'Neural Networks from Scratch','ch':'Sentdex','u':'https://www.youtube.com/watch?v=Wo5dMEP_BbI'}],
    'tensorflow':[{'t':'TensorFlow 2.0 Full Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=tPYj3fFJGjk'}],
    'pytorch':[{'t':'PyTorch Full Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=c36lUUr864M'}],
    'react':[{'t':'React JS Full Course','ch':'Dave Gray','u':'https://www.youtube.com/watch?v=RVFAyFWO4go'},{'t':'React Tutorial','ch':'Programming with Mosh','u':'https://www.youtube.com/watch?v=SqcY0GlETPk'}],
    'node.js':[{'t':'Node.js Tutorial','ch':'Programming with Mosh','u':'https://www.youtube.com/watch?v=TlB_eWDSMt4'}],
    'docker':[{'t':'Docker Tutorial','ch':'TechWorld with Nana','u':'https://www.youtube.com/watch?v=3c-iBn73dDE'},{'t':'Docker Full Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=fqMOX6JJhGo'}],
    'kubernetes':[{'t':'Kubernetes Tutorial','ch':'TechWorld with Nana','u':'https://www.youtube.com/watch?v=X48VuDVv0do'}],
    'aws':[{'t':'AWS Certified Cloud Practitioner','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=SOTamWNgDKc'}],
    'git':[{'t':'Git and GitHub Crash Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=RGOj5yH7evk'},{'t':'Git Tutorial','ch':'Programming with Mosh','u':'https://www.youtube.com/watch?v=8JJ101D3knE'}],
    'linux':[{'t':'Linux Command Line Full Course','ch':'freeCodeCamp','u':'https://www.youtube.com/watch?v=iwolPf6kN-k'}],
    'default':[{'t':'CS50 – Intro to Computer Science','ch':'Harvard','u':'https://www.youtube.com/watch?v=8mAITcNt710'}],
}

QBANK = {
    'python':[
        {'q':'What is the output of print(type([]))?','o':["<class 'list'>","<class 'array'>","<class 'tuple'>","Error"],'a':0},
        {'q':'Which keyword defines a function in Python?','o':['func','define','def','function'],'a':2},
        {'q':"What does len('hello') return?",'o':['4','5','6','Error'],'a':1},
        {'q':'Which data type is mutable?','o':['tuple','string','list','int'],'a':2},
        {'q':'How do you create an empty dictionary?','o':['d=[]','d=()','d={}','d=<>'],'a':2},
        {'q':"What does 'self' refer to in a class?",'o':['Parent class','The class itself','Current instance','Global variable'],'a':2},
        {'q':'What is a lambda function?','o':['Recursive function','Anonymous inline function','Class method','Built-in function'],'a':1},
        {'q':'Which method removes and returns the last list element?','o':['remove()','delete()','pop()','discard()'],'a':2},
        {'q':"What does 'yield' do?",'o':['Returns and exits','Creates a generator','Raises exception','Imports module'],'a':1},
        {'q':'What is list comprehension?','o':['Sort method','Compact way to create lists','A type of loop','List function'],'a':1},
        {'q':'Which exception is raised on division by zero?','o':['ValueError','TypeError','ZeroDivisionError','ArithmeticError'],'a':2},
        {'q':'What does the @ symbol do in Python?','o':['Matrix multiply / decorator','String format','Bitwise AND','Power operator'],'a':0},
    ],
    'java':[
        {'q':'Which keyword inherits a class in Java?','o':['implements','inherits','extends','super'],'a':2},
        {'q':'Size of int in Java?','o':['2 bytes','4 bytes','8 bytes','OS dependent'],'a':1},
        {'q':'Entry point of a Java program?','o':['start()','run()','main()','init()'],'a':2},
        {'q':'What does JVM stand for?','o':['Java Virtual Memory','Java Variable Machine','Java Virtual Machine','Java Version Manager'],'a':2},
        {'q':'Most restrictive access modifier?','o':['public','protected','private','default'],'a':2},
        {'q':'What is an interface?','o':['Concrete class','Abstract type with method signatures','Variable type','Exception class'],'a':1},
        {'q':"What does 'final' do to a variable?",'o':['Makes it global','Makes it constant','Makes it volatile','Makes it static'],'a':1},
        {'q':'What is autoboxing?','o':['Manual conversion','Auto conversion between primitives and wrappers','Memory management','Design pattern'],'a':1},
        {'q':'Which collection maintains insertion order?','o':['HashSet','TreeSet','LinkedList','HashMap'],'a':2},
        {'q':'What is a NullPointerException?','o':['Null file access','Dereferencing null reference','Integer overflow','Array out of bounds'],'a':1},
        {'q':"What does 'static' mean?",'o':['Thread-safe','Belongs to class not instance','Immutable','Abstract'],'a':1},
        {'q':'What is method overloading?','o':['Overriding parent','Same name different params','Recursion','Inheritance'],'a':1},
    ],
    'javascript':[
        {'q':'Block-scoped variable declaration?','o':['var','let','const','let and const'],'a':3},
        {'q':'What does === check?','o':['Only value','Only type','Value and type','Neither'],'a':2},
        {'q':'typeof null returns?','o':['null','undefined','object','string'],'a':2},
        {'q':'Adds to end of array?','o':['push()','pop()','shift()','append()'],'a':0},
        {'q':'What is a closure?','o':['Loop construct','Function with outer scope access','Class method','Async function'],'a':1},
        {'q':'What does async/await do?','o':['Speeds code','Handles async operations synchronously','Creates threads','Optimises loops'],'a':1},
        {'q':'What does Array.map() return?','o':['undefined','A new array','Same array modified','A boolean'],'a':1},
        {'q':'What is a Promise?','o':['Variable declaration','Object for eventual async completion','A loop','A class'],'a':1},
        {'q':"What does 'use strict' do?",'o':['Enables ES6','Stricter parsing and error handling','Imports modules','Enables async'],'a':1},
        {'q':'Removes first array element?','o':['pop()','shift()','splice()','delete()'],'a':1},
        {'q':'What is hoisting?','o':['DOM manipulation','Declarations moved to top of scope','CSS property','Event handler'],'a':1},
        {'q':'What is the prototype chain?','o':['CSS selector','Linked object inheritance chain','Promise chain','Import chain'],'a':1},
    ],
    'sql':[
        {'q':'Filters rows after grouping?','o':['WHERE','HAVING','FILTER','GROUP BY'],'a':1},
        {'q':'SELECT DISTINCT does what?','o':['Selects NULLs','Returns unique rows','Sorts results','Joins tables'],'a':1},
        {'q':'Returns all rows from both tables?','o':['INNER JOIN','LEFT JOIN','RIGHT JOIN','FULL OUTER JOIN'],'a':3},
        {'q':'What is a PRIMARY KEY?','o':['Foreign reference','Unique non-null identifier','An index','A view'],'a':1},
        {'q':'Removes all rows without deleting table?','o':['DELETE','DROP','TRUNCATE','REMOVE'],'a':2},
        {'q':'What is a foreign key?','o':['Primary key alias','References primary key in another table','Unique constraint','Index'],'a':1},
        {'q':'What does GROUP BY do?','o':['Sorts results','Groups rows by value','Filters rows','Joins tables'],'a':1},
        {'q':'What is a SQL VIEW?','o':['Stored query as virtual table','Physical table copy','Stored procedure','Trigger'],'a':0},
        {'q':'Counts non-null values?','o':['SUM()','COUNT()','AVG()','TOTAL()'],'a':1},
        {'q':'ORDER BY DESC does?','o':['Ascending','Descending','Random','Alphabetical only'],'a':1},
        {'q':'What is a subquery?','o':['Simplified query','Query nested inside another','Stored procedure','View'],'a':1},
        {'q':'What does COALESCE() do?','o':['Joins tables','Returns first non-null','Counts rows','Rounds numbers'],'a':1},
    ],
    'machine learning':[
        {'q':'Algorithm for classification?','o':['Linear Regression','K-Means','Logistic Regression','PCA'],'a':2},
        {'q':'What is overfitting?','o':['Model too simple','Good train bad test','Low accuracy','Too little data'],'a':1},
        {'q':'Cross-validation is used for?','o':['Data cleaning','Evaluation and tuning','Feature extraction','Augmentation'],'a':1},
        {'q':'Regression evaluation metric?','o':['Accuracy','F1-Score','RMSE','Precision'],'a':2},
        {'q':'PCA stands for?','o':['Principal Component Analysis','Partial Cluster Algorithm','Predictive Classification Analysis','None'],'a':0},
        {'q':'What is a confusion matrix?','o':['Data structure','Table of prediction vs actual','Loss function','Activation function'],'a':1},
        {'q':'What is gradient descent?','o':['Normalization method','Optimization to minimize loss','Feature selection','Clustering'],'a':1},
        {'q':'What is bias-variance tradeoff?','o':['Speed vs accuracy','Underfitting vs overfitting','Memory vs speed','Precision vs recall'],'a':1},
        {'q':'Random Forest consists of?','o':['Single decision tree','Multiple decision trees','Neural layers','SVM kernels'],'a':1},
        {'q':'Regularization is used for?','o':['Speed training','Prevent overfitting','Increase model size','Normalize data'],'a':1},
        {'q':'K-Means is used for?','o':['Classification','Regression','Clustering','Dimensionality reduction'],'a':2},
        {'q':'ROC curve plots?','o':['Loss over epochs','TPR vs FPR','Accuracy vs loss','Data distribution'],'a':1},
    ],
    'docker':[
        {'q':'What is a Docker image?','o':['Running container','Read-only template','Network bridge','Storage volume'],'a':1},
        {'q':'Command to run a container?','o':['docker start','docker run','docker exec','docker build'],'a':1},
        {'q':'File that defines a Docker image?','o':['docker-compose.yml','Dockerfile','docker.config','container.json'],'a':1},
        {'q':'docker ps shows?','o':['All images','Running containers','All volumes','Network settings'],'a':1},
        {'q':'EXPOSE in Dockerfile does?','o':['Opens firewall','Documents port container listens on','Maps host port','Creates network'],'a':1},
        {'q':'docker-compose is for?','o':['Single containers','Multi-container apps','Pushing to registry','Monitoring'],'a':1},
        {'q':'What is a Docker volume?','o':['Network plugin','Persistent container storage','Image layer','Runtime config'],'a':1},
        {'q':'docker pull does?','o':['Pushes image','Downloads image from registry','Runs container','Builds image'],'a':1},
        {'q':'Multi-stage build achieves?','o':['Multiple containers','Reduces image size','Speeds builds','Multiple images'],'a':1},
        {'q':'docker exec does?','o':['Starts container','Runs command inside running container','Builds image','Removes container'],'a':1},
        {'q':'What is a Docker registry?','o':['Container runtime','Repository for images','Networking component','Monitoring tool'],'a':1},
        {'q':'COPY vs ADD in Dockerfile?','o':['No difference','ADD supports URLs/tar; COPY is simpler','COPY deprecated','ADD faster'],'a':1},
    ],
    'git':[
        {'q':'Initialises a new Git repo?','o':['git start','git init','git new','git create'],'a':1},
        {'q':'git commit -m does?','o':['Merges branches','Stages files','Saves snapshot with message','Pushes to remote'],'a':2},
        {'q':'Creates a new branch?','o':['git branch name','git new branch','git make name','git start name'],'a':0},
        {'q':'git pull does?','o':['Pushes changes','Fetches and merges from remote','Creates tag','Deletes branch'],'a':1},
        {'q':'What is a merge conflict?','o':['Network error','Two branches edited same line differently','Deleted file','Empty commit'],'a':1},
        {'q':'git stash does?','o':['Deletes uncommitted','Temporarily saves uncommitted changes','Commits all','Merges branches'],'a':1},
        {'q':'What is a pull request?','o':['Pulling code','Request to merge changes into branch','Git command','Webhook'],'a':1},
        {'q':'git rebase does?','o':['Removes commits','Moves commits onto new base','Creates backup','Pushes to origin'],'a':1},
        {'q':'.gitignore is for?','o':['Ignoring commands','Files git should not track','User config','Adding files'],'a':1},
        {'q':'git reset --hard does?','o':['Resets staged only','Discards changes resets to last commit','New branch','Merge to main'],'a':1},
        {'q':'git cherry-pick does?','o':['Select best commits','Apply specific commit to another branch','Revert commit','Squash commits'],'a':1},
        {'q':'git tag does?','o':['Renames branch','Marks commit with label','Lists branches','Shows history'],'a':1},
    ],
    'react':[
        {'q':'What is JSX?','o':['JS runtime','Syntax extension for JS in React','CSS framework','Testing library'],'a':1},
        {'q':'Hook for state in functional components?','o':['useEffect','useRef','useState','useContext'],'a':2},
        {'q':'Virtual DOM does?','o':['Replaces real DOM','Updates only changed parts','Slows rendering','Handles APIs'],'a':1},
        {'q':'What is a React prop?','o':['Internal state','A hook','Data from parent to child','Lifecycle method'],'a':2},
        {'q':'Hook that runs after every render?','o':['useState','useEffect','useRef','useMemo'],'a':1},
        {'q':'What is a controlled component?','o':['No state component','Input controlled by React state','Pure component','Class component'],'a':1},
        {'q':'React.memo() does?','o':['Creates memoized value','Prevents re-render if props unchanged','Manages state','Fetches data'],'a':1},
        {'q':'Context API is for?','o':['Routing','Global state without prop drilling','Styling','API calls'],'a':1},
        {'q':'Key prop in lists is?','o':['CSS class','Unique ID for React to track items','Event handler','State variable'],'a':1},
        {'q':'useCallback does?','o':['Caches computed value','Returns memoized callback','Fetches data','Manages refs'],'a':1},
        {'q':'Code splitting in React?','o':['Split CSS','Load app chunks on demand','Divide components','Separate state'],'a':1},
        {'q':'useEffect vs useLayoutEffect?','o':['No difference','useLayoutEffect fires sync after DOM','useEffect deprecated','useLayoutEffect async'],'a':1},
    ],
    'default':[
        {'q':'API stands for?','o':['Application Protocol Interface','Application Programming Interface','Automated Program Instruction','Advanced Programming Interface'],'a':1},
        {'q':'What is a REST API?','o':['Database type','A language','Architectural style for web services','Cloud service'],'a':2},
        {'q':'CI/CD stands for?','o':['Code Integration/Deployment','Continuous Integration/Continuous Deployment','Cloud Infrastructure/Delivery','None'],'a':1},
        {'q':'Agile methodology is?','o':['A language','Database approach','Iterative project management','Cloud model'],'a':2},
        {'q':'Version control is?','o':['Code speed','Tracking file changes over time','Database type','API style'],'a':1},
        {'q':'Cloud computing is?','o':['Local server mgmt','Computing services over internet','Programming paradigm','Database'],'a':1},
        {'q':'Microservice architecture?','o':['Monolithic app','Small independent services','Database design','Frontend pattern'],'a':1},
        {'q':'DevOps is?','o':['Language','Dev + Ops for faster delivery','Cloud provider','Testing framework'],'a':1},
        {'q':'Containerisation is?','o':['Physical servers','Packaging app with dependencies','Database sharding','Encryption'],'a':1},
        {'q':'Load balancing is?','o':['Code optimisation','Traffic across multiple servers','Security technique','Caching'],'a':1},
        {'q':'CDN stands for?','o':['Database type','Network delivering content by location','Programming tool','Cloud DB'],'a':1},
        {'q':'OAuth is?','o':['Database protocol','Open standard for access delegation','CSS framework','Server runtime'],'a':1},
    ],
}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def extract_skills(text):
    low = text.lower()
    found = []
    for skill in ALL_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, low):
            found.append(skill)
    return found

def extract_text_from_pdf(path):
    text = ''
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + '\n'
    return text

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    d = request.json
    name  = d.get('name','').strip()
    email = d.get('email','').strip().lower()
    dept  = d.get('dept','').strip()
    pw    = d.get('password','')
    if not all([name, email, dept, pw]):
        return jsonify({'error':'All fields required'}), 400
    if len(pw) < 6:
        return jsonify({'error':'Password must be 6+ chars'}), 400
    try:
        with get_db() as db:
            db.execute('INSERT INTO users (name,email,password,dept) VALUES (?,?,?,?)',
                       (name, email, hash_pw(pw), dept))
        return jsonify({'message':'Registered successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'error':'Email already registered'}), 409

@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    email = d.get('email','').strip().lower()
    pw    = d.get('password','')
    with get_db() as db:
        user = db.execute('SELECT * FROM users WHERE email=? AND password=?',
                          (email, hash_pw(pw))).fetchone()
    if not user:
        return jsonify({'error':'Invalid email or password'}), 401
    token = make_token(user['id'])
    return jsonify({
        'token': token,
        'user': {'id':user['id'],'name':user['name'],'email':user['email'],'dept':user['dept'],'theme':user['theme']}
    })

@app.route('/api/me', methods=['GET'])
@token_required
def me():
    with get_db() as db:
        user = db.execute('SELECT * FROM users WHERE id=?', (request.user_id,)).fetchone()
    return jsonify({'id':user['id'],'name':user['name'],'email':user['email'],'dept':user['dept'],'theme':user['theme']})

@app.route('/api/theme', methods=['POST'])
@token_required
def update_theme():
    theme = request.json.get('theme','light')
    with get_db() as db:
        db.execute('UPDATE users SET theme=? WHERE id=?', (theme, request.user_id))
    return jsonify({'message':'Theme updated'})

# ── RESUME / ANALYSIS ROUTES ──────────────────────────────────────────────────
@app.route('/api/upload-resume', methods=['POST'])
@token_required
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'error':'No file uploaded'}), 400
    file = request.files['resume']
    if not allowed_file(file.filename):
        return jsonify({'error':'Only PDF and TXT files allowed'}), 400
    filename = secure_filename(f"user_{request.user_id}_{file.filename}")
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)
    try:
        ext = filename.rsplit('.',1)[1].lower()
        if ext == 'pdf':
            text = extract_text_from_pdf(path)
        else:
            with open(path, 'r', errors='ignore') as f:
                text = f.read()
    except Exception as e:
        return jsonify({'error':f'Failed to read file: {str(e)}'}), 500
    return jsonify({'text': text, 'filename': filename})

@app.route('/api/analyze', methods=['POST'])
@token_required
def analyze():
    d = request.json
    company = d.get('company','')
    role    = d.get('role','')
    date    = d.get('interview_date','')
    text    = d.get('raw_text','')
    if not all([company, role, date, text]):
        return jsonify({'error':'Missing fields'}), 400
    required = ROLE_SKILLS.get(role, [])
    found    = extract_skills(text)
    matched  = [s for s in required if s in found]
    missing  = [s for s in required if s not in found]
    extra    = [s for s in found if s not in required][:12]
    pct      = round(len(matched)/len(required)*100) if required else 0
    alts = []
    for r, skills in ROLE_SKILLS.items():
        if r == role: continue
        m = [s for s in skills if s in found]
        miss = [s for s in skills if s not in found]
        alts.append({'role':r,'matched':m,'missing':miss,'pct':round(len(m)/len(skills)*100)})
    alts.sort(key=lambda x: len(x['missing']))
    return jsonify({
        'company':company,'role':role,'interview_date':date,
        'matched':matched,'missing':missing,'extra':extra,
        'pct':pct,'eligible':pct>=50,
        'best_alt': alts[0] if alts and alts[0]['pct'] > pct else None,
        'all_alts': alts[:3]
    })

@app.route('/api/application', methods=['POST'])
@token_required
def save_application():
    d = request.json
    company       = d['company']
    role          = d['role']
    date          = d['interview_date']
    raw_text      = d.get('raw_text','')
    matched       = json.dumps(d.get('matched',[]))
    found         = json.dumps(d.get('found',[]))
    skill_items   = d.get('skill_items',[])
    pct           = d.get('pct',0)
    with get_db() as db:
        # delete old
        old = db.execute('SELECT id FROM applications WHERE user_id=?',(request.user_id,)).fetchone()
        if old:
            db.execute('DELETE FROM skill_items WHERE app_id=?',(old['id'],))
            db.execute('DELETE FROM applications WHERE id=?',(old['id'],))
        cur = db.execute(
            'INSERT INTO applications (user_id,company,role,interview_date,raw_text,matched_skills,found_skills,match_pct) VALUES (?,?,?,?,?,?,?,?)',
            (request.user_id,company,role,date,raw_text,matched,found,pct)
        )
        app_id = cur.lastrowid
        for sk in skill_items:
            db.execute('INSERT INTO skill_items (app_id,skill_name,done,deadline) VALUES (?,?,?,?)',
                       (app_id, sk['name'], 0, sk['deadline']))
    return jsonify({'message':'Saved','app_id':app_id})

@app.route('/api/application', methods=['GET'])
@token_required
def get_application():
    with get_db() as db:
        app_row = db.execute('SELECT * FROM applications WHERE user_id=? ORDER BY id DESC LIMIT 1',(request.user_id,)).fetchone()
        if not app_row:
            return jsonify({'application':None})
        skills = db.execute('SELECT * FROM skill_items WHERE app_id=?',(app_row['id'],)).fetchall()
    return jsonify({'application':{
        'id':app_row['id'],'company':app_row['company'],'role':app_row['role'],
        'interview_date':app_row['interview_date'],'raw_text':app_row['raw_text'],
        'matched':json.loads(app_row['matched_skills'] or '[]'),
        'found':json.loads(app_row['found_skills'] or '[]'),
        'pct':app_row['match_pct'],
        'skill_items':[{'id':s['id'],'name':s['skill_name'],'done':bool(s['done']),'deadline':s['deadline']} for s in skills]
    }})

@app.route('/api/skill/<int:skill_id>/complete', methods=['POST'])
@token_required
def complete_skill(skill_id):
    with get_db() as db:
        db.execute('UPDATE skill_items SET done=1, completed_at=CURRENT_TIMESTAMP WHERE id=?',(skill_id,))
    return jsonify({'message':'Skill marked complete'})

@app.route('/api/skill/<int:skill_id>/undo', methods=['POST'])
@token_required
def undo_skill(skill_id):
    with get_db() as db:
        db.execute('UPDATE skill_items SET done=0, completed_at=NULL WHERE id=?',(skill_id,))
    return jsonify({'message':'Skill unmarked'})

@app.route('/api/application/switch-role', methods=['POST'])
@token_required
def switch_role():
    d = request.json
    new_role     = d['role']
    skill_items  = d['skill_items']
    new_matched  = json.dumps(d.get('matched',[]))
    with get_db() as db:
        app_row = db.execute('SELECT id FROM applications WHERE user_id=? ORDER BY id DESC LIMIT 1',(request.user_id,)).fetchone()
        if not app_row: return jsonify({'error':'No application'}), 404
        app_id = app_row['id']
        db.execute('UPDATE applications SET role=?, matched_skills=? WHERE id=?',(new_role,new_matched,app_id))
        db.execute('DELETE FROM skill_items WHERE app_id=?',(app_id,))
        for sk in skill_items:
            db.execute('INSERT INTO skill_items (app_id,skill_name,done,deadline) VALUES (?,?,?,?)',
                       (app_id,sk['name'],0,sk['deadline']))
    return jsonify({'message':'Role switched'})

# ── QUIZ ROUTES ───────────────────────────────────────────────────────────────
@app.route('/api/quiz/<skill_name>', methods=['GET'])
@token_required
def get_quiz(skill_name):
    key = skill_name.lower()
    bank = QBANK.get(key, QBANK['default'])
    all_idx = list(range(len(bank)))
    with get_db() as db:
        seen = [r['q_index'] for r in db.execute(
            'SELECT q_index FROM quiz_history WHERE user_id=? AND skill_name=?',
            (request.user_id, key)).fetchall()]
    available = [i for i in all_idx if i not in seen]
    if len(available) < 3:
        # reset history for this skill
        with get_db() as db:
            db.execute('DELETE FROM quiz_history WHERE user_id=? AND skill_name=?',(request.user_id,key))
        available = all_idx[:]
    import random
    random.shuffle(available)
    picked = available[:3]
    # record as seen
    with get_db() as db:
        for i in picked:
            db.execute('INSERT INTO quiz_history (user_id,skill_name,q_index) VALUES (?,?,?)',(request.user_id,key,i))
    # shuffle options per question
    questions = []
    for i in picked:
        q = dict(bank[i])
        opts_idx = list(range(len(q['o'])))
        random.shuffle(opts_idx)
        new_opts = [q['o'][x] for x in opts_idx]
        new_a    = opts_idx.index(q['a'])
        questions.append({'q':q['q'],'o':new_opts,'a':new_a})
    return jsonify({'questions': questions})

# ── VIDEO ROUTE ───────────────────────────────────────────────────────────────
@app.route('/api/videos/<skill_name>', methods=['GET'])
@token_required
def get_videos(skill_name):
    key = skill_name.lower()
    vids = VIDEOS.get(key, VIDEOS['default'])
    return jsonify({'videos': vids})

# ── SERVE FRONTEND ────────────────────────────────────────────────────────────
@app.route('/', defaults={'path':''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.template_folder, 'index.html')

if __name__ == '__main__':
    print("\n✅ SkillSync AI backend running at http://localhost:5000\n")
    app.run(debug=True, port=5000)
