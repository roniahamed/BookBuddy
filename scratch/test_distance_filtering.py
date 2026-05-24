import requests

def test_distance():
    url = "http://10.10.13.10:8002/api/v1/books"
    
    # 1. Test using lat/lng aliases
    params_alias = {
        "page": 1,
        "per_page": 5,
        "lat": 23.72564,
        "lng": 90.3973998,
        "sort_by": "distance"
    }
    
    print("Testing with 'lat' and 'lng' aliases...")
    r = requests.get(url, params=params_alias)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    items = data.get("items", [])
    
    print(f"Total books found: {data.get('total')}")
    assert len(items) > 0, "No books returned"
    
    # Verify that distance is NOT null
    for item in items:
        dist = item.get("distance_km")
        print(f"Book ID: {item['id']}, Title: '{item['title']}', Distance: {dist} km")
        assert dist is not None, f"Expected distance_km to be calculated, got None for book {item['id']}"
    
    # Verify that it is sorted by distance ascending
    distances = [item["distance_km"] for item in items if item["distance_km"] is not None]
    assert distances == sorted(distances), f"Expected distances to be sorted, got {distances}"
    print("✅ Aliases (lat/lng) and sorting by distance verified successfully!")

    # 2. Test using original user_lat/user_lon
    params_original = {
        "page": 1,
        "per_page": 5,
        "user_lat": 23.72564,
        "user_lon": 90.3973998,
        "sort_by": "nearby"
    }
    
    print("\nTesting with original 'user_lat' and 'user_lon' parameters...")
    r = requests.get(url, params=params_original)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    items = data.get("items", [])
    
    for item in items:
        dist = item.get("distance_km")
        print(f"Book ID: {item['id']}, Title: '{item['title']}', Distance: {dist} km")
        assert dist is not None, f"Expected distance_km to be calculated, got None for book {item['id']}"
        
    distances = [item["distance_km"] for item in items if item["distance_km"] is not None]
    assert distances == sorted(distances), f"Expected distances to be sorted, got {distances}"
    print("✅ Backwards compatibility with 'user_lat'/'user_lon' verified successfully!")

if __name__ == "__main__":
    test_distance()
