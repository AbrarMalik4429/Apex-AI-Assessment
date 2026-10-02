---
doc_id: faq-patient
title: "Patient FAQs"
category: faq
entity: "Patient FAQs"
default_confidence: DEMO_CONFIG
last_verified: 2026-09-28
review_by: 2027-09-28
language: en
sources:
  - name: "Booking workflow documentation and clinic policies (docs 12)"
  - name: "CHI regulatory framework (doc 00) and insurer documents (docs 01-04)"
  - name: "Emergency numbers, health services and first-aid documents (docs 10, 11, 13)"
---
# Patient FAQs

Each answer summarises the detailed documents and keeps their confidence tags. Where the demo configuration does not define something, the answer says so and hands over to a person instead of guessing.

## Booking and appointments

### How do I book an appointment?
You can book by doctor name, by specialty, by describing your reason so I can suggest a specialty, by returning to a doctor you have seen before, or by scheduling a follow-up your doctor already created. I check the doctor's availability and your own existing appointments before confirming. `[DEMO_CONFIG]`
Also asked as: Can I make an appointment? Book me with Dr. X. I need a cardiologist.

### I do not know which doctor or specialty I need
Describe your reason for the visit and I can suggest a specialty to consider, and list matching doctors. This is a suggestion only, not a diagnosis, and you choose the doctor. For anything urgent, call 997 or 911 instead. `[DEMO_CONFIG]`

### How far ahead can I book?
Availability is shown for up to 90 days ahead. This is a configurable default, not a fixed clinic rule. `[DEMO_CONFIG]`

### Why can I not see any available slots?
A slot may already be taken, the doctor may be on leave at that time, you may already have an appointment that overlaps, or the date may be outside the 90-day window. I can check other dates or another doctor. `[DEMO_CONFIG]`

### Can I book two appointments at the same time?
No. I check your own appointments and will not confirm a booking that overlaps one you already have. `[DEMO_CONFIG]`

### How do I reschedule an appointment?
Tell me which appointment and the new date or time. I check the new slot is free, then move the booking and keep a record of the change. Rescheduling within 24 hours of the appointment needs a team member's approval. `[DEMO_CONFIG]`

### How do I cancel an appointment?
Tell me which appointment. Cancellations more than 24 hours ahead are processed automatically; cancellations within 24 hours are passed to a team member for approval. `[DEMO_CONFIG]`

### Is there a cancellation fee or a penalty for missing an appointment?
The demo configuration defines no cancellation fee or no-show penalty, so I cannot state one. I can hand you to a team member to confirm the clinic's rules. `[DEMO_CONFIG]`

### How do I book a follow-up appointment?
When your doctor recommends a follow-up, it appears as an unscheduled follow-up linked to your earlier visit. Tell me and I will show the doctor's available times so you can choose one. `[DEMO_CONFIG]`

### I did not get a confirmation. Is my booking made?
I only confirm a booking, change or cancellation after the system has confirmed it. If you are unsure, I can look up your appointments, and if the system did not respond I will pass this to a team member rather than assume it worked. `[DEMO_CONFIG]`

### Can I book or change an appointment for a family member?
The demo assistant only works with the appointments of the verified patient in this session. Booking for someone else is not supported, so I will hand you to a team member. `[DEMO_CONFIG]`

### What are the clinic's opening hours, address and phone number?
The demo configuration does not define these, so I do not have them confirmed. I can hand you to a team member who can help. `[DEMO_CONFIG]`

### Does the clinic offer video or online consultations?
The demo configuration does not define this. Separately, the Ministry of Health's Seha and Sehhaty apps offer tele-consultations. `[DEMO_CONFIG]` `[TYPICAL]`

## Insurance

### Does my insurance cover this treatment?
I cannot confirm what your own policy will pay. I can explain what is typically covered and the statutory minimum that CHI-regulated policies must include, and then point you to your policy document or insurer to confirm. `[DEMO_CONFIG]`

### Does this clinic accept my insurance company?
The demo configuration does not say which insurers this clinic works with. The knowledge base describes Tawuniya, Bupa Arabia, Al Rajhi Takaful and MedGulf in general terms only, which does not mean the clinic accepts them. I can hand you to a team member to confirm. `[DEMO_CONFIG]`

### What is the maximum my insurance will pay per year?
For CHI-regulated policies the statutory floor is SAR 1,000,000 per person per year. `[REGULATORY]` Actual limits depend on the policy: for example, Tawuniya's published My Family tiers ranged from SAR 30,000 to SAR 250,000 and Bupa Family from SAR 75,000 to SAR 250,000. `[INSURER]` Check your own policy schedule.

### What is a co-payment or deductible?
It is the share of a claim you pay yourself. For CHI-regulated policies the out-patient co-payment is 20%, capped at SAR 100, and there is no co-insurance on in-patient services. `[REGULATORY]`

### Are medicines covered, and what do I pay?
Formulary medicines are covered, and the CHI floor is a 20% co-payment capped at SAR 30. `[REGULATORY]` Medicines outside the insurer's formulary may be declined or self-paid. `[TYPICAL]`

### Are surgeries and hospital stays covered?
In-patient care and surgery are covered within the annual limit, with no co-insurance on in-patient services. `[REGULATORY]` Elective surgery normally needs insurer pre-approval. `[TYPICAL]` Cosmetic surgery and weight-loss surgery are generally excluded, and Bupa Family explicitly excludes sleeve gastrectomy. `[TYPICAL]` `[INSURER]`

### Is maternity covered?
Childbirth complications are covered under the CHI floor. `[REGULATORY]` Normal-delivery cover on basic plans is typically up to about SAR 15,000, and many lower plans exclude maternity or offer it as an add-on, so confirm with your insurer. `[TYPICAL]`

### Are dental and optical covered?
The CHI floor includes essential and preventive dental up to SAR 1,800, root canal and dental emergencies up to SAR 1,200, and vision up to SAR 1,000 with a frame limit of SAR 400. `[REGULATORY]` Basic plans often cover only emergency dental and optical care. `[TYPICAL]`

### Is mental health treatment covered?
The CHI floor includes psychiatric treatment up to SAR 50,000, and from 2026 Category B and C plans include up to 10 psychiatric consultations per year. `[REGULATORY]` Confirm the details with your insurer.

### Are pre-existing and chronic conditions covered?
The CHI floor covers chronic and pre-existing conditions, but individual contracts may still apply waiting periods that vary widely, so I cannot give a single figure. `[REGULATORY]` `[VARIES]`

### What is pre-authorization?
It is the insurer's approval before certain services, such as elective surgery, MRI or CT, non-emergency admission or maternity admission. The provider usually requests it. `[TYPICAL]`

### What do Class A, B and C mean?
They are insurer package tiers, not official CHI classes. Class A generally means the broadest private network and highest limits, B a mid-range network, and C a basic or government-linked network. `[TYPICAL]`

### What if I go to a hospital outside my network?
Non-emergency treatment outside your insurer's network is usually not covered, and you may pay the full cost. Emergency treatment is treated differently. `[TYPICAL]`

### How do I check that my policy is active?
The CHI Insurance Information Inquiry e-service shows active policy details, the insurer and the network. Your insurance card and HR documents also show your network. `[TYPICAL]`

### Can I cancel my insurance policy and get a refund?
Employer-mandated policies generally cannot be cancelled by the employee mid-term. Individual policies can usually be cancelled and the unused premium refunded. Details vary by insurer. `[TYPICAL]` `[VARIES]`

### How do I complain about my insurance company?
Complain to the insurer first, which is expected to respond within about 15 business days. `[TYPICAL]` Then escalate to the Insurance Authority (customer care 8001240551). `[OFFICIAL]`

## Emergencies and safety

### What is the ambulance number in Saudi Arabia?
997, the Saudi Red Crescent. 911 also works, and 999 is police and 998 is civil defense. `[OFFICIAL]`

### Someone has collapsed and is not breathing. What do I do?
Call 997 or 911 now, or have someone call, and start hands-only CPR: push hard and fast in the centre of the chest, about 5 cm deep, 100 to 120 times per minute, until help takes over. `[GUIDELINE]` I can walk you through the steps.

### Someone is choking. What do I do?
Call 997 or 911. If they cannot cough, speak or breathe, give up to 5 back blows between the shoulder blades, then up to 5 abdominal thrusts, and alternate. Babies under one year get back blows and chest thrusts, not abdominal thrusts. `[GUIDELINE]`

### When should I call an ambulance instead of booking an appointment?
Call 997 or 911 for life-threatening problems such as a suspected heart attack, stroke, choking, severe bleeding, unconsciousness or serious breathing trouble. `[TYPICAL]` I will not book an appointment for an emergency.

### Is there a 24-hour health advice line?
Yes, the Ministry of Health's 937 line runs 24 hours a day with doctors for advice and poisoning guidance. `[OFFICIAL]`

### Who can I call if I am struggling emotionally?
The Ministry of Health psychological consultation line is 920033360 (confirm its hours), and 937 is open 24 hours. `[OFFICIAL]` `[VARIES]` If you are in immediate danger or thinking of harming yourself, call 997 or 911, and I will pass you to a team member.

## General health system

### Is healthcare free in Saudi Arabia?
Government facilities are free for Saudi citizens. `[OFFICIAL]` Expatriates must hold CHI-compliant health insurance, and non-urgent care is paid through it. `[TYPICAL]`

### What should I bring to my appointment?
Your Iqama or national ID and your insurance card, plus any earlier reports or prescriptions relevant to the visit. `[TYPICAL]` `[DEMO_CONFIG]`

### How do I book at a government primary healthcare centre?
The Ministry of Health's Mawid app books, reschedules and cancels appointments at Ministry primary healthcare centres. It is separate from this clinic's booking system. `[TYPICAL]`

## About this assistant

### Am I talking to a real person?
No, I am an AI assistant. I can hand you to a team member at any time. `[DEMO_CONFIG]`

### Can you diagnose my symptoms or tell me what treatment to take?
No. I do not diagnose or recommend treatment. In an emergency I will tell you to call 997 or 911 and can share standard first-aid steps while help is on the way. `[DEMO_CONFIG]`

### Can you see my family's or anyone else's appointments?
No. I only work with the appointments of the patient verified in this session, and I never accept a patient ID typed into the chat. `[DEMO_CONFIG]`

### Is my information private?
I only show you your own information. I cannot make claims about legal or regulatory compliance in this demo, and full phone-number and one-time-passcode verification is planned for production. `[DEMO_CONFIG]`

### Can you make mistakes?
Yes. For anything important, such as insurance cover or a booking, please check the confirmation or ask for a team member to verify. `[DEMO_CONFIG]`

### How do I talk to a human?
Just ask. I will also hand over if a request stays unclear, a system action fails, a cancellation falls inside 24 hours, or you describe an emergency. `[DEMO_CONFIG]`
