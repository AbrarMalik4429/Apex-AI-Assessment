-- Reconcile the existing synthetic demo schedule. Administrator connection required.
BEGIN;
DO $$
BEGIN
 IF EXISTS (
 SELECT 1 FROM booking.slot s JOIN booking.doctor d USING(doctor_id)
 JOIN booking.bookings b USING(slot_id)
 WHERE d.doctor_name IN ('Dr. Amal Demo','Dr. Sami Demo') AND s.day_of_week IN (5,6)
 ) THEN RAISE EXCEPTION 'Weekend templates have booking references; no schedule changes applied'; END IF;
END $$;
DELETE FROM booking.slot s USING booking.doctor d
WHERE s.doctor_id=d.doctor_id AND d.doctor_name IN ('Dr. Amal Demo','Dr. Sami Demo')
AND s.day_of_week IN (5,6);
INSERT INTO booking.slot (slot_id,doctor_id,day_of_week,start_time,end_time)
SELECT gen_random_uuid(),d.doctor_id,w.weekday,t.start_at,t.start_at + interval '30 minutes'
FROM booking.doctor d CROSS JOIN generate_series(0,4) w(weekday)
CROSS JOIN (VALUES (time '09:00'),(time '09:30'),(time '10:00'),(time '10:30'),(time '11:00'),(time '11:30'),(time '14:00'),(time '14:30')) t(start_at)
WHERE d.doctor_name IN ('Dr. Amal Demo','Dr. Sami Demo')
AND NOT EXISTS (SELECT 1 FROM booking.slot s WHERE s.doctor_id=d.doctor_id
AND s.day_of_week=w.weekday AND s.start_time=t.start_at AND s.end_time=t.start_at+interval '30 minutes');
COMMIT;
