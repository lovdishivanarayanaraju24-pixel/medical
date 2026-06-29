from PIL import Image, ImageDraw

def create_mock_report():
    # Large canvas
    img = Image.new('RGB', (800, 1000), color='white')
    d = ImageDraw.Draw(img)
    
    # Write report text
    text_lines = [
        "PATIENT: Jane Doe",
        "DOB: 1990-05-15",
        "DATE: 2026-06-28",
        "HOSPITAL: Metro Health Clinic",
        "DOCTOR: Dr. Alice Smith",
        "",
        "TEST RESULTS:",
        "------------------------------------",
        "Glucose       110.0   mg/dL   (70.0 - 100.0)",
        "Hemoglobin    14.2    g/dL    (12.0 - 17.5)",
        "Creatinine    0.9     mg/dL   (0.6 - 1.2)",
        "Bilirubin     0.8     mg/dL   (0.1 - 1.2)",
        "",
        "PRESCRIPTIONS / MEDICATIONS:",
        "Metformin 500mg - Take 1 tablet daily"
    ]
    
    y = 50
    for line in text_lines:
        # Draw basic lines
        d.text((50, y), line, fill="black")
        y += 40
        
    img.save("c:/Users/VAISHNAVI/OneDrive/Desktop/hackthon-3/mock_report.png")
    print("Mock report image created.")

if __name__ == "__main__":
    create_mock_report()
