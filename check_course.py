from app import app, db
from app import Course, Classroom

with app.app_context():
    cs101 = Course.query.filter_by(code='CS101').first()
    print(f"CS101 - min_capacity: {cs101.min_capacity}, required_equipment: '{cs101.required_equipment}'")
    
    classrooms = Classroom.query.all()
    print("\nClassrooms:")
    for room in classrooms:
        print(f"  {room.room_number} - Capacity: {room.capacity}, Equipment: '{room.equipment}'")
        
        # Check if this classroom is suitable for CS101
        suitable = (room.capacity >= cs101.min_capacity and 
                   (not cs101.required_equipment or cs101.required_equipment in room.equipment))
        print(f"    Suitable for CS101: {suitable}")
