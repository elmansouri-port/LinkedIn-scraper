@app.route('/data', methods=['POST'])
def receive_data():
    # Get the JSON data from the request
    data = request.get_json()

    # Check if data is received
    if not data:
        return jsonify({
            "status": "error",
            "message": "No data received"
        }), 400

    try:
        # Extract the clientToken from custom_data
        client_token = data.get("data", {}).get("custom_data", {}).get("clientToken")
        if not client_token:
            return jsonify({
                "status": "error",
                "message": "clientToken not found in custom_data"
            }), 400

        # Extract the status from the subscription data
        subscription_status = data.get("data", {}).get("status")
        if not subscription_status:
            return jsonify({
                "status": "error",
                "message": "status not found in subscription data"
            }), 400

        # Find the user by the clientToken (stored in the token field in the User table)
        user = User.query.filter_by(token=client_token).first()
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found with the provided clientToken"
            }), 404

        # Update the user's balance with the subscription status
        user.balance = subscription_status
        db.session.commit()

        # Return a success response
        return jsonify({
            "status": "success",
            "message": "User balance updated successfully",
            "user_id": user.id,
            "new_balance": user.balance
        }), 200

    except Exception as e:
        # Handle any unexpected errors
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500
