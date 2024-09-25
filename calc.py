from flask import Flask, render_template, request, jsonify
from itertools import groupby
from operator import itemgetter

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Rate per km for transport cost
COST_PER_KM = {
    'ace': 35,
    'pickup': 45
}
CLUBBING_DISTANCE = 30

def round_to_nearest_10(value):
    return round(value / 10) * 10

def calculate_transport_costs(entries, vehicle_type, manual_cost=None):
    results = []
    
    # Sort entries by distance
    sorted_entries = sorted(entries, key=itemgetter('distance'))
    
    # Group entries by distance (club orders with distance < 30 km)
    grouped_entries = []
    for distance, group in groupby(sorted_entries, key=itemgetter('distance')):
        group_list = list(group)
        if distance < CLUBBING_DISTANCE and len(grouped_entries) > 0:
            grouped_entries[-1].extend(group_list)
        else:
            grouped_entries.append(group_list)
    
    # Find the maximum distance for transport cost calculation
    max_distance = max(entry['distance'] for entry in entries)
    
    # Calculate the total transport cost
    if manual_cost is not None:
        total_transport_cost = manual_cost
    else:
        total_transport_cost = max_distance * COST_PER_KM[vehicle_type]

    # Calculate clubbed amount-distance products and total amount-distance product
    clubbed_amount_distance_products = [sum(entry['amount'] * entry['distance'] for entry in group) for group in grouped_entries]
    total_amount_distance_product = sum(clubbed_amount_distance_products)

    # Calculate transport cost for each group
    for group, clubbed_amount_distance_product in zip(grouped_entries, clubbed_amount_distance_products):
        group_transport_cost = (clubbed_amount_distance_product / total_amount_distance_product) * total_transport_cost
        
        # Distribute group transport cost among parties in the group
        group_total_amount_distance_product = sum(entry['amount'] * entry['distance'] for entry in group)
        for entry in group:
            party_name = entry['partyName']
            amount = entry['amount']
            pincode = entry['pincode']
            distance = entry['distance']

            # Calculate each party's share of the group transport cost based on amount-distance product ratio
            amount_distance_product = amount * distance
            transport_cost_share = (amount_distance_product / group_total_amount_distance_product) * group_transport_cost

            # Round transport cost share to nearest 10
            rounded_transport_cost = round_to_nearest_10(transport_cost_share)

            # Determine color based on the condition
            if rounded_transport_cost >= (distance * COST_PER_KM[vehicle_type]) - 500:
                color = 'red'
            else:
                color = 'green'

            results.append({
                'partyName': party_name,
                'amount': amount,
                'pincode': pincode,
                'distance': distance,
                'transportCost': rounded_transport_cost,  # Use rounded cost
                'color': color
            })

    return results

# Route to render the HTML form
@app.route('/')
def index():
    return render_template('index.html')

# Route to calculate transport costs
@app.route('/calculate', methods=['POST'])
def calculate():
    # Extract form data
    vehicle_type = request.form.get('vehicleType')
    manual_cost = request.form.get('manualCost')
    party_names = request.form.getlist('partyName[]')
    amounts = request.form.getlist('amount[]')
    pincodes = request.form.getlist('pincode[]')
    distances = request.form.getlist('distance[]')

    entries = []

    # Create a list of dictionaries for each entry
    for party_name, amount, pincode, distance in zip(party_names, amounts, pincodes, distances):
        entries.append({
            'partyName': party_name,
            'amount': float(amount),
            'pincode': pincode,
            'distance': float(distance)
        })

    # Calculate the transport costs
    if manual_cost and manual_cost.strip():
        results = calculate_transport_costs(entries, vehicle_type, float(manual_cost))
    else:
        results = calculate_transport_costs(entries, vehicle_type)

    # Return results as JSON
    return jsonify(results)

# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True)
