from flask import Blueprint , jsonify , request
from models import SuperUser , db , User
from flask_jwt_extended import jwt_required , create_access_token , get_jwt_identity
from datetime import timedelta
from flask_cors import CORS

super_user_bp = Blueprint('super_user_bp' , __name__)

CORS(super_user_bp)

# @super_user_bp.route('/super_user/dashboard' , methods = ['GET'])

@super_user_bp.route('/super_user ' , methods = ['GET'])
# @jwt_required()
# def super_user_dashboard():
#     return jsonify({
#         "message": "Welcome to the Super User Dashboard!"
#     }), 200

def get_super_user():
    data = request.json
    try:
        new_super_user = SuperUser(
            username = data.get('username'),
            email = data.get('email'),
            password = data.get('password')
        )
        db.session.add(new_super_user)
        db.session.commit()
        return jsonify({'message':'Super user created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create super user", "error": str(e)}), 400
    
@super_user_bp.route('/super_user/add' , methods = ['POST'])
def create_super_user():
    data = request.json
    try:
        new_super_user = SuperUser(
            username = data.get('username'),
            email = data.get('email'),
            password = data.get('password')
        )
        db.session.add(new_super_user)
        db.session.commit()
        return jsonify({'message':'Super user created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create super user", "error": str(e)}), 400
    
@super_user_bp.route('/super_user/test' , methods = ['GET'])
def super_user_test():
    return jsonify({"message":"Super User route is working!"}), 200

@super_user_bp.route('/super_user/update' , methods = ['PUT'])
def update_super_user():
    data = request.json
    try:
        super_user_id = data.get('super_user_id')
        super_user = SuperUser.query.get_or_404(super_user_id)
        super_user.username = data.get('username' , super_user.username)
        super_user.email = data.get('email' , super_user.email)
        db.session.commit()
        return jsonify({"message":"Super user updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}) , 500
    
@super_user_bp.route('/super_user/delete/<string:super_user_id>' , methods = ['DELETE'])
def delete_super_user(super_user_id):
    try:
        super_user = SuperUser.query.get_or_404(super_user_id)
        db.session.delete(super_user)
        db.session.commit()
        return jsonify({"message":"Super user deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}) , 500
    
@super_user_bp.route('/super_user/login' , methods = ['POST'])
def super_user_login(): 
    data = request.json
    email = data.get('email')
    password = data.get('password')
    super_user = SuperUser.query.filter_by(email=email).first()
    if not super_user or not super_user.check_password(password):
        return jsonify({"message":"Invalid email or password"}), 401
    access_token = create_access_token(identity=super_user.super_user_id , expires_delta=timedelta(hours=2))
    return jsonify({
        "message":"Login successful",
        "access_token":access_token
    }) , 200

@super_user_bp.route('/super_user/logout' , methods = ['POST'])
@jwt_required() 
def super_user_logout():
    return jsonify({"message":"Logout successful"}), 200

@super_user_bp.route('/super_user/register' , methods = ['POST'])
def register_super_user():
    data = request.json
    try:
        new_super_user = SuperUser(
            username = data.get('username'),
            email = data.get('email'),
            password = data.get('password')
        )
        db.session.add(new_super_user)
        db.session.commit()
        return jsonify({'message':'Super user registered successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to register super user", "error": str(e)}), 400

@super_user_bp.route('/super_user/users' , methods = ['GET'])
@jwt_required()
def get_all_users():
    try:
        users = User.query.all()
        result = []
        for user in users:
            user_dict = {
                'user_id' : user.user_id,
                'username' : user.username,
                'email' : user.email,
                'role' : user.role,
                'created_at' : user.created_at
            }
            result.append(user_dict)
        return jsonify(result) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
@super_user_bp.route('/super_user/users/<string:user_id>' , methods = ['GET'])
@jwt_required()
def get_user_by_id(user_id):
    try:
        user = User.query.get_or_404(user_id)
        user_dict = {
            'user_id' : user.user_id,
            'username' : user.username,
            'email' : user.email,
            'role' : user.role,
            'created_at' : user.created_at
        }
        return jsonify(user_dict) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
@super_user_bp.route('/super_user/users/<string:user_id>' , methods = ['DELETE'])
@jwt_required()
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message":"User deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}) , 500

@super_user_bp.route('/super_user/users/<string:user_id>' , methods = ['PUT'])
@jwt_required()
def update_user(user_id):
    data = request.json
    try:
        user = User.query.get_or_404(user_id)
        user.username = data.get('username' , user.username)
        user.email = data.get('email' , user.email)
        user.role = data.get('role' , user.role)
        db.session.commit()
        return jsonify({"message":"User updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}) , 500
    
@super_user_bp.route('/super_user/users' , methods = ['POST'])
@jwt_required()
def create_user():
    data = request.json
    try:
        new_user = User(
            username = data.get('username'),
            email = data.get('email'),
            password = data.get('password'),
            role = data.get('role')
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message':'User created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create user", "error": str(e)}), 400
    
@super_user_bp.route('/super_user/profile' , methods = ['GET'])
@jwt_required()
def get_super_user_profile():
    try:
        super_user_id = get_jwt_identity()
        super_user = SuperUser.query.get_or_404(super_user_id)
        super_user_dict = {
            'super_user_id' : super_user.super_user_id,
            'username' : super_user.username,
            'email' : super_user.email,
            'created_at' : super_user.created_at
        }
        return jsonify(super_user_dict) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
@super_user_bp.route('/super_user/profile' , methods = ['PUT'])
@jwt_required()
def update_super_user_profile():
    data = request.json
    try:
        super_user_id = get_jwt_identity()
        super_user = SuperUser.query.get_or_404(super_user_id)
        super_user.username = data.get('username' , super_user.username)
        super_user.email = data.get('email' , super_user.email)
        db.session.commit()
        return jsonify({"message":"Super user profile updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}) , 500
    
@super_user_bp.route('/super_user/change_password' , methods = ['PUT'])
@jwt_required()
def change_super_user_password():
    data = request.json
    try:
        super_user_id = get_jwt_identity()
        super_user = SuperUser.query.get_or_404(super_user_id)
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        if not super_user.check_password(current_password):
            return jsonify({"message":"Current password is incorrect"}), 401
        super_user.set_password(new_password)
        db.session.commit()
        return jsonify({"message":"Password changed successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}) , 500
    
@super_user_bp.route('/super_user/users/count' , methods = ['GET'])
@jwt_required()
def get_user_count():
    try:
        user_count = User.query.count()
        return jsonify({"user_count":user_count}) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500