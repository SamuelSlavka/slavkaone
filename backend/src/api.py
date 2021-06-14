import os, flask, flask_sqlalchemy, flask_praetorian, json, sys
import psql, etherum, constants

from flask_cors import CORS, cross_origin
from model import User

db = User._db
guard = flask_praetorian.Praetorian()

# Initialize flask app
app = flask.Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'top secret'
app.config['JWT_ACCESS_LIFESPAN'] = {'hours': 24}
app.config['JWT_REFRESH_LIFESPAN'] = {'days': 30}


# Initializes CORS
cors = CORS(app, resources={"/api/*": {"origins": "*"}})
app.config['CORS_HEADERS'] = 'Content-Type'


# Token blacklist
blacklist = set()

#check if token is valid
def is_blacklisted(jti):
    return jti in blacklist

# create psql message and contract database
psql.createTables()

# Initialize a local user database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.getcwd(), 'database.db')}"
db.init_app(app)

with app.app_context():
    db.create_all()

# create and deploy smart contract
res = etherum.init_eth_with_PK(constants.PK)

if not res['result']:
    sys.exit("Error connecting to ETH")
if res['new_contract']:
    with app.app_context():
        db.drop_all()
        db.create_all()        

# Initialize the flask-praetorian instance for the app
guard.init_app(app, User, is_blacklisted=is_blacklisted)

# Set up some routes
@app.route('/api/')
@cross_origin()
def home():
    ret = etherum.get_last_transaction()
    return ret, 200

# Logs in user
@app.route('/api/register', methods=['POST'])
@cross_origin()
def register():
    req = flask.request.get_json(force=True)
    username = req.get('username', None)
    password = req.get('password', None)
    new_user = User(
            username= username,
            address= "",
            password= guard.hash_password(password)
    )
    if username is None or password is None:
        return {'access_token':''},400
    if db.session.query(User).filter_by(username = username).first() is not None:
        return {'access_token':''},400

    db.session.add(new_user)
    db.session.commit()

    user = guard.authenticate(username, password)
    
    ret = {'access_token': guard.encode_jwt_token(user)}
    return ret, 200

# Logs in user
@app.route('/api/login', methods=['POST'])
@cross_origin()
def login():
    req = flask.request.get_json(force=True)
    username = req.get('username', None)
    password = req.get('password', None)
    address = req.get('address', None)
    user = guard.authenticate(username, password)

    ret = {'access_token': guard.encode_jwt_token(user)}
    return ret, 200

# Returns contract info
@app.route('/api/info', methods=['POST'])
@cross_origin()
@flask_praetorian.auth_required
def info():    
    res = psql.getContract()
    ret = {'address': res[1], 'abi':res[2], 'userAddr':flask_praetorian.current_user().address, 'username':flask_praetorian.current_user().username}
    return ret, 200

# Adds address
@app.route('/api/saveAddress', methods=['POST'])
@cross_origin()
@flask_praetorian.auth_required
def saveAddr():
    req = flask.request.get_json(force=True)
    address = req.get('address', None)
    publicKey = req.get('public', None)
    if address is not None and publicKey is not None:
        flask_praetorian.current_user().address = address
        db.session.commit()
        flask_praetorian.current_user().publicKey = publicKey
        db.session.commit()
    ret = {'result': 'success'}
    return ret, 200   

# Adds address and return contract info
@app.route('/api/contacts', methods=['POST'])
@cross_origin()
@flask_praetorian.auth_required
def contacts():
    req = flask.request.get_json(force=True)
    address = req.get('address', None)
    
    res = psql.getContacts(address)
    ret = {'result':res}
    return ret, 200

#recvAddress, sendAddress, recvName, sendName, timestamp, recvContents, sendContents
# Saves message into db
@app.route('/api/savemessage', methods=['POST'])
@cross_origin()
@flask_praetorian.auth_required
def savemessage():
    req = flask.request.get_json(force=True)
    recvAddress = req.get('recvAddress', None)
    sendAddress = req.get('sendAddress', None)
    recvName = req.get('recvName', None)
    sendName = req.get('sendName', None)    
    timestamp = req.get('timestamp', None)
    recvContents = req.get('recvContents', None)
    sendContents = req.get('sendContents', None)
    
    psql.setMessage(recvAddress, sendAddress, recvName, sendName, timestamp, recvContents, sendContents)

    ret = {'result': 'success'}
    return ret, 200

# Get all messages for user from db
@app.route('/api/getmessages', methods=['POST'])
@cross_origin()
@flask_praetorian.auth_required
def getmessage():
    req = flask.request.get_json(force=True)
    raddress = req.get('recvAddress', None)
    saddress = req.get('sendAddress', None)

    res = psql.getMessages(raddress, saddress)
    ret = {'result':res}
    return ret, 200

# Disables an JWT
@app.route('/api/logout', methods=['POST'])
@cross_origin()
def logout():
    req = flask.request.get_json(force=True)        
    if req is not None:
        token = req.get('token', None)        
        data = guard.extract_jwt_token(token)
        blacklist.add(data['jti'])
    return flask.jsonify(message='token blacklisted')


# Refreshes an existing JWT
@app.route('/api/refresh', methods=['POST'])
@cross_origin()
def refresh():    
    old_token = request.get_data()
    new_token = guard.refresh_jwt_token(old_token)
    ret = {'access_token': new_token}
    return ret, 200

# Protected endpoint
@app.route('/api/protected')
@cross_origin()
@flask_praetorian.auth_required
def protected():
    return {"username": flask_praetorian.current_user().username, "address": flask_praetorian.current_user().address}


# Protected endpoint
@app.route('/api/poor', methods=['POST'])
@cross_origin()
@flask_praetorian.auth_required
def poor():
    req = flask.request.get_json(force=True)
    ret = {"result": 0} 
    if req is not None:
        address = req.get('address', None)             
        res = etherum.reqest_founds(address,constants.PK)      
        ret = {"result": 1}
    return ret, 200

# Protected endpoint
@app.route('/api/public', methods=['POST'])
@cross_origin()
@flask_praetorian.auth_required
def publicKey():
    req = flask.request.get_json(force=True)
    res = {"result": 0}
    if req is not None:
        address = req.get('address', None)           
        username = req.get('username', None)
        with app.app_context():
            ret = db.session.query(User.publicKey).filter(User.address == address).first()
        if (len(ret) > 0):
            res = {"result": ret[0]}        
    return res, 200

# Protected endpoint
@app.route('/api/provider', methods=['POST'])
@cross_origin()
def getProvider():    
    res = {"result": constants.PROVIDER}        
    return res, 200


# Run the example
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)