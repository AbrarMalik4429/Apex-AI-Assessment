-- Initial schema snapshot. Apply with alembic upgrade head.

CREATE SCHEMA booking;

REVOKE ALL ON SCHEMA booking FROM PUBLIC;

CREATE TABLE booking.doctor (
	doctor_id UUID NOT NULL, 
	doctor_name VARCHAR(120) NOT NULL, 
	specialty_1 VARCHAR(100) NOT NULL, 
	specialty_2 VARCHAR(100), 
	specialty_3 VARCHAR(100), 
	PRIMARY KEY (doctor_id)
);

ALTER TABLE booking.doctor ENABLE ROW LEVEL SECURITY;

CREATE TABLE booking.patient (
	patient_id UUID NOT NULL, 
	patient_name VARCHAR(120) NOT NULL, 
	phone_number VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (patient_id)
);

ALTER TABLE booking.patient ENABLE ROW LEVEL SECURITY;

CREATE TABLE booking.bookings (
	booking_id UUID NOT NULL, 
	patient_id UUID NOT NULL, 
	doctor_id UUID NOT NULL, 
	appointment_date DATE, 
	booked_day_of_week INTEGER, 
	booked_start_time TIME WITHOUT TIME ZONE, 
	booked_end_time TIME WITHOUT TIME ZONE, 
	type VARCHAR(100) NOT NULL, 
	dependent_on_booking_id UUID, 
	superseded_by_booking_id UUID, 
	status VARCHAR(24) NOT NULL, 
	notes VARCHAR(500), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (booking_id), 
	CONSTRAINT booking_status CHECK (status IN ('confirmed','pending_scheduling','cancelled','no_show','completed','rescheduled')), 
	CONSTRAINT booking_complete_time CHECK ((appointment_date IS NULL AND booked_day_of_week IS NULL AND booked_start_time IS NULL AND booked_end_time IS NULL) OR (appointment_date IS NOT NULL AND booked_day_of_week IS NOT NULL AND booked_start_time IS NOT NULL AND booked_end_time IS NOT NULL)), 
	CONSTRAINT confirmed_has_time CHECK (status != 'confirmed' OR appointment_date IS NOT NULL), 
	CONSTRAINT pending_has_no_time CHECK (status != 'pending_scheduling' OR appointment_date IS NULL), 
	CONSTRAINT booking_time_order CHECK (booked_end_time > booked_start_time), 
	CONSTRAINT booking_weekday CHECK (booked_day_of_week BETWEEN 0 AND 6), 
	CONSTRAINT booking_not_own_parent CHECK (dependent_on_booking_id != booking_id), 
	FOREIGN KEY(patient_id) REFERENCES booking.patient (patient_id), 
	FOREIGN KEY(doctor_id) REFERENCES booking.doctor (doctor_id), 
	FOREIGN KEY(dependent_on_booking_id) REFERENCES booking.bookings (booking_id), 
	FOREIGN KEY(superseded_by_booking_id) REFERENCES booking.bookings (booking_id)
);

CREATE INDEX ix_bookings_doctor_date_status ON booking.bookings (doctor_id, appointment_date, status);

CREATE INDEX ix_bookings_patient_date_status ON booking.bookings (patient_id, appointment_date, status);

ALTER TABLE booking.bookings ENABLE ROW LEVEL SECURITY;

CREATE TABLE booking.doctor_leave (
	leave_id UUID NOT NULL, 
	doctor_id UUID NOT NULL, 
	start_datetime TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_datetime TIMESTAMP WITH TIME ZONE NOT NULL, 
	reason VARCHAR(250), 
	PRIMARY KEY (leave_id), 
	CONSTRAINT leave_time_order CHECK (end_datetime > start_datetime), 
	FOREIGN KEY(doctor_id) REFERENCES booking.doctor (doctor_id)
);

CREATE INDEX ix_leave_doctor_end ON booking.doctor_leave (doctor_id, end_datetime);

ALTER TABLE booking.doctor_leave ENABLE ROW LEVEL SECURITY;

CREATE TABLE booking.patient_session (
	session_id UUID NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	patient_id UUID NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	state JSON NOT NULL, 
	PRIMARY KEY (session_id), 
	UNIQUE (token_hash), 
	FOREIGN KEY(patient_id) REFERENCES booking.patient (patient_id)
);

ALTER TABLE booking.patient_session ENABLE ROW LEVEL SECURITY;

CREATE TABLE booking.slot (
	slot_id UUID NOT NULL, 
	doctor_id UUID NOT NULL, 
	day_of_week INTEGER NOT NULL, 
	start_time TIME WITHOUT TIME ZONE NOT NULL, 
	end_time TIME WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (slot_id), 
	CONSTRAINT slot_weekday CHECK (day_of_week BETWEEN 0 AND 6), 
	CONSTRAINT slot_time_order CHECK (end_time > start_time), 
	FOREIGN KEY(doctor_id) REFERENCES booking.doctor (doctor_id)
);

CREATE INDEX ix_slot_doctor_weekday ON booking.slot (doctor_id, day_of_week);

ALTER TABLE booking.slot ENABLE ROW LEVEL SECURITY;

CREATE TABLE booking.operation (
	session_id UUID NOT NULL, 
	request_id UUID NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	response JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (session_id, request_id), 
	FOREIGN KEY(session_id) REFERENCES booking.patient_session (session_id)
);

ALTER TABLE booking.operation ENABLE ROW LEVEL SECURITY;
