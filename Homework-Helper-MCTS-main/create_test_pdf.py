"""Create a simple test PDF for testing"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

# Create test PDF
pdf_path = os.path.expanduser("~") + "\\Downloads\\test_homework.pdf"
c = canvas.Canvas(pdf_path, pagesize=letter)

c.drawString(50, 750, "Sample Homework Document")
c.drawString(50, 730, "=" * 50)
c.drawString(50, 700, "Physics: Newton's Laws of Motion")
c.drawString(50, 670, "")
c.drawString(50, 640, "Newton's First Law (Law of Inertia):")
c.drawString(100, 610, "An object at rest stays at rest, and an object in motion")
c.drawString(100, 590, "stays in motion unless acted upon by a net external force.")
c.drawString(50, 560, "")
c.drawString(50, 530, "Newton's Second Law (F = ma):")
c.drawString(100, 500, "The acceleration of an object is directly proportional to")
c.drawString(100, 480, "the net force acting on it and inversely proportional to")
c.drawString(100, 460, "its mass.")
c.drawString(50, 430, "")
c.drawString(50, 400, "Newton's Third Law (Action-Reaction):")
c.drawString(100, 370, "For every action, there is an equal and opposite reaction.")
c.drawString(50, 340, "")
c.drawString(50, 310, "Example Problem:")
c.drawString(100, 280, "A 5 kg object is pushed with a force of 20 N.")
c.drawString(100, 260, "What is the acceleration of the object?")
c.drawString(100, 240, "Solution: F = ma => a = F/m = 20N / 5kg = 4 m/s²")

c.save()
print(f"Test PDF created at: {pdf_path}")
print(f"You can upload this PDF to test the PDF processing functionality")
