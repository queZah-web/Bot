-- «ضافني»: منو ضاف كل عضو (0 = دخل بنفسه بالرابط، NULL = ما نعرف)
ALTER TABLE group_members ADD COLUMN added_by INTEGER;
