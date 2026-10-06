"""
AI Feature 3 : Spam / fake listing detection
--------------------------------------------
Multinomial Naive Bayes text classifier (TF-IDF words + bigrams) trained on
a small labelled dataset of genuine and spam listings (below).

On top of the ML probability, three simple rules add explainable reasons:
  - phone number / link / "whatsapp" inside the text
  - price higher than the original price
  - price suspiciously low (< 5% of original price)

If the final score >= 0.5 the listing is saved with status 'pending' and
is_flagged = 1. A database trigger then notifies all admins, who approve
or reject it from the admin panel.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# 1 = spam / fake, 0 = genuine
TRAINING_DATA = [
    ("Engineering mathematics textbook by B S Grewal, few highlights, good condition", 0),
    ("Casio fx-991ES scientific calculator, works perfectly, used for 2 semesters", 0),
    ("Database system concepts Korth 6th edition, no torn pages", 0),
    ("Mini drafter for engineering drawing, all parts included", 0),
    ("Lab coat size M, washed and clean, used in chemistry lab", 0),
    ("Arduino Uno board with USB cable, used in one mini project", 0),
    ("Hero cycle with lock and basket, new tyres last month", 0),
    ("Study table lamp LED with 3 brightness levels", 0),
    ("Electric kettle 1.5 litre, used in hostel, works fine", 0),
    ("Dell laptop i5 8GB RAM, battery backup 3 hours, charger included", 0),
    ("Data structures using C notes and book, selling as set", 0),
    ("Cricket bat English willow, light use, with cover", 0),
    ("Mattress single bed 4 inch, clean, leaving hostel so selling", 0),
    ("Multimeter digital for electronics lab, with probes", 0),
    ("Operating system concepts Galvin, 9th edition, good condition", 0),
    ("Wireless mouse Logitech, battery included", 0),
    ("Breadboard and jumper wires kit for circuits lab", 0),
    ("Drawing board A1 size with clips", 0),
    ("Python programming book for beginners, like new", 0),
    ("Bucket and mug set for hostel room, barely used", 0),
    ("Formal shoes size 9 used for placements only twice", 0),
    ("Raspberry Pi 4 2GB with case and power adapter", 0),
    ("Earn money fast!!! Work from home, contact on whatsapp now", 1),
    ("FREE iPhone giveaway click the link to claim your prize", 1),
    ("Get rich quick crypto investment double your money guaranteed", 1),
    ("Call now 9876543210 best deal limited offer hurry", 1),
    ("100% original Apple MacBook only Rs 2000 pay advance first", 1),
    ("Send advance payment via UPI and get product delivered, no meeting", 1),
    ("Lottery winner claim now, share your OTP to receive gift", 1),
    ("Join our telegram channel for free exam papers leak", 1),
    ("Buy followers and likes cheap, instagram growth service", 1),
    ("Brand new PS5 just Rs 999 urgent sale pay first on gpay", 1),
    ("Part time job earn 5000 daily no experience click here", 1),
    ("Assignment and exam writing service guaranteed pass contact whatsapp", 1),
    ("Investment scheme refer friends and earn commission bonus", 1),
    ("Cheap branded watches replica first copy whatsapp for catalog", 1),
    ("Free recharge offer visit www site link now limited time", 1),
    ("Selling answers of upcoming semester exam paper, pay now", 1),
]

_PHONE = re.compile(r"(\+91[\s-]?)?[6-9]\d{9}")
_LINK = re.compile(r"(https?://|www\.|bit\.ly|\.com\b)", re.I)
_CONTACT_WORDS = re.compile(r"\b(whatsapp|telegram|gpay|upi|advance payment|otp)\b", re.I)

_model = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True),
    MultinomialNB(alpha=0.5),
)
_model.fit([t for t, _ in TRAINING_DATA], [y for _, y in TRAINING_DATA])


def check_listing(title, description, price, original_price):
    """Returns {'score': 0..1, 'is_spam': bool, 'reasons': [...]}"""
    text = f"{title} {description}"
    ml_prob = float(_model.predict_proba([text])[0][1])
    reasons = []
    score = ml_prob

    if ml_prob >= 0.5:
        reasons.append(f"Text looks like spam ({round(ml_prob * 100)}% by Naive Bayes model)")
    if _PHONE.search(text) or _LINK.search(text) or _CONTACT_WORDS.search(text):
        reasons.append("Contains phone number / link / off-platform payment words")
        score = max(score, 0.6)
    if original_price and price and price > original_price * 1.05:
        reasons.append("Price is higher than the original price")
        score = max(score, 0.55)
    if original_price and price and price < original_price * 0.05:
        reasons.append("Price is suspiciously low (< 5% of original)")
        score = max(score, 0.55)

    return {"score": round(score, 2), "is_spam": score >= 0.5, "reasons": reasons}
