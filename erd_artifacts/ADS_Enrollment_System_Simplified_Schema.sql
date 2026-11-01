-- =============================================================
-- ADS Enrollment System (Simplified)
-- Business Schema Export - 15 Tables
-- Generated: 2026-10-30 16:38:23
--
-- SOURCE
--   Server-generated DDL obtained with SHOW CREATE TABLE against the
--   migrated MySQL database of this simplified Django project.
--   Nothing in this file is hand-written or reconstructed.
--
-- SCOPE
--   This file contains ONLY the 15 approved business tables.
--
--   Django framework tables are INTENTIONALLY EXCLUDED. That covers the
--   authentication, permission, session, content-type, admin-log,
--   migration-history and user-join tables owned by Django itself.
--
--   Legacy tables removed in the simplified design are also absent.
--
-- NOTES
--   - Schema only: definitions of structure, never data.
--   - No database-creation or schema-selection statements, so this file
--     can be imported into any empty MySQL schema.
--   - Runtime auto-increment table counters are stripped, so imported
--     tables start their ids at 1.
--   - Storage engine InnoDB, character set utf8mb4, collation
--     utf8mb4_unicode_ci throughout.
--   - Contains 15 PRIMARY KEY, 19 FOREIGN KEY, 17 UNIQUE KEY and
--     14 CHECK constraints.
--   - enrollment_detail.ck_enrollment_detail_psu_grade enforces the PSU
--     1.00-5.00 scale with exactly 11 allowed values. INC and DRP are
--     represented by result_status, never by a numeric grade. Only an
--     explicitly recorded PASSED result satisfies a prerequisite.
-- =============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE `app_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `middle_name` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `college` (
  `id` int NOT NULL AUTO_INCREMENT,
  `college_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_college_college_code` (`college_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `program` (
  `id` int NOT NULL AUTO_INCREMENT,
  `program_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` longtext COLLATE utf8mb4_unicode_ci,
  `is_active` tinyint(1) NOT NULL,
  `college_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_program_program_code` (`program_code`),
  KEY `program_college_id_e033918f_fk_college_id` (`college_id`),
  CONSTRAINT `program_college_id_e033918f_fk_college_id` FOREIGN KEY (`college_id`) REFERENCES `college` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `curriculum` (
  `id` int NOT NULL AUTO_INCREMENT,
  `curriculum_code` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `effective_year` int NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `program_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_curriculum_program_code` (`program_id`,`curriculum_code`),
  CONSTRAINT `curriculum_program_id_19b1cc86_fk_program_id` FOREIGN KEY (`program_id`) REFERENCES `program` (`id`),
  CONSTRAINT `ck_curriculum_effective_year_positive` CHECK ((`effective_year` >= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `course` (
  `id` int NOT NULL AUTO_INCREMENT,
  `course_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` longtext COLLATE utf8mb4_unicode_ci,
  `units` decimal(4,1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_course_course_code` (`course_code`),
  CONSTRAINT `ck_course_units_positive` CHECK ((`units` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `curriculum_course` (
  `id` int NOT NULL AUTO_INCREMENT,
  `year_level` int NOT NULL,
  `recommended_semester` int NOT NULL,
  `course_category` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` int NOT NULL,
  `curriculum_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_curriculum_course_pair` (`curriculum_id`,`course_id`),
  KEY `curriculum_course_course_id_7d898ba3_fk_course_id` (`course_id`),
  CONSTRAINT `curriculum_course_course_id_7d898ba3_fk_course_id` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`),
  CONSTRAINT `curriculum_course_curriculum_id_f2fa7d78_fk_curriculum_id` FOREIGN KEY (`curriculum_id`) REFERENCES `curriculum` (`id`),
  CONSTRAINT `ck_curriculum_course_semester_positive` CHECK ((`recommended_semester` >= 1)),
  CONSTRAINT `ck_curriculum_course_year_level_positive` CHECK ((`year_level` >= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `course_prerequisite` (
  `id` int NOT NULL AUTO_INCREMENT,
  `course_id` int NOT NULL,
  `prerequisite_course_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_course_prerequisite_pair` (`course_id`,`prerequisite_course_id`),
  KEY `course_prerequisite_prerequisite_course_id_c493ebf2_fk_course_id` (`prerequisite_course_id`),
  CONSTRAINT `course_prerequisite_course_id_eb4de4e5_fk_course_id` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`),
  CONSTRAINT `course_prerequisite_prerequisite_course_id_c493ebf2_fk_course_id` FOREIGN KEY (`prerequisite_course_id`) REFERENCES `course` (`id`),
  CONSTRAINT `ck_course_prerequisite_not_self` CHECK ((`course_id` <> `prerequisite_course_id`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `academic_term` (
  `id` int NOT NULL AUTO_INCREMENT,
  `academic_year` varchar(9) COLLATE utf8mb4_unicode_ci NOT NULL,
  `semester_number` int NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `enrollment_open` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_academic_term_year_semester` (`academic_year`,`semester_number`),
  CONSTRAINT `ck_academic_term_date_range` CHECK ((`end_date` >= `start_date`)),
  CONSTRAINT `ck_academic_term_semester_positive` CHECK ((`semester_number` >= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `student` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_number` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `year_level` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `curriculum_id` int NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  UNIQUE KEY `uq_student_student_number` (`student_number`),
  KEY `student_curriculum_id_badd0d48_fk_curriculum_id` (`curriculum_id`),
  CONSTRAINT `student_curriculum_id_badd0d48_fk_curriculum_id` FOREIGN KEY (`curriculum_id`) REFERENCES `curriculum` (`id`),
  CONSTRAINT `student_user_id_dcc2526f_fk_app_user_id` FOREIGN KEY (`user_id`) REFERENCES `app_user` (`id`),
  CONSTRAINT `ck_student_year_level_positive` CHECK ((`year_level` >= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `instructor` (
  `id` int NOT NULL AUTO_INCREMENT,
  `employee_number` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  UNIQUE KEY `uq_instructor_employee_number` (`employee_number`),
  CONSTRAINT `instructor_user_id_4f34f9dd_fk_app_user_id` FOREIGN KEY (`user_id`) REFERENCES `app_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `section` (
  `id` int NOT NULL AUTO_INCREMENT,
  `section_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `capacity` int NOT NULL,
  `room_code` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `day_of_week` int DEFAULT NULL,
  `start_time` time(6) DEFAULT NULL,
  `end_time` time(6) DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` int NOT NULL,
  `instructor_id` int DEFAULT NULL,
  `term_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_section_course_term_code` (`course_id`,`term_id`,`section_code`),
  KEY `section_instructor_id_47df603b_fk_instructor_id` (`instructor_id`),
  KEY `section_term_id_577da78d_fk_academic_term_id` (`term_id`),
  CONSTRAINT `section_course_id_e7e21e73_fk_course_id` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`),
  CONSTRAINT `section_instructor_id_47df603b_fk_instructor_id` FOREIGN KEY (`instructor_id`) REFERENCES `instructor` (`id`),
  CONSTRAINT `section_term_id_577da78d_fk_academic_term_id` FOREIGN KEY (`term_id`) REFERENCES `academic_term` (`id`),
  CONSTRAINT `ck_section_capacity_positive` CHECK ((`capacity` >= 1)),
  CONSTRAINT `ck_section_day_of_week_range` CHECK (((`day_of_week` is null) or ((`day_of_week` >= 0) and (`day_of_week` <= 6)))),
  CONSTRAINT `ck_section_time_range` CHECK (((`start_time` is null) or (`end_time` is null) or (`end_time` > `start_time`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `enrollment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `enrollment_date` datetime(6) NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_id` int NOT NULL,
  `term_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_enrollment_student_term` (`student_id`,`term_id`),
  KEY `enrollment_term_id_65b55301_fk_academic_term_id` (`term_id`),
  CONSTRAINT `enrollment_student_id_75934c6f_fk_student_id` FOREIGN KEY (`student_id`) REFERENCES `student` (`id`),
  CONSTRAINT `enrollment_term_id_65b55301_fk_academic_term_id` FOREIGN KEY (`term_id`) REFERENCES `academic_term` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `enrollment_detail` (
  `id` int NOT NULL AUTO_INCREMENT,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `enrolled_at` datetime(6) NOT NULL,
  `final_grade` decimal(4,2) DEFAULT NULL,
  `result_status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recorded_at` datetime(6) DEFAULT NULL,
  `enrollment_id` int NOT NULL,
  `section_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_enrollment_detail_section` (`enrollment_id`,`section_id`),
  KEY `enrollment_detail_section_id_b8399fb7_fk_section_id` (`section_id`),
  CONSTRAINT `enrollment_detail_enrollment_id_92149a09_fk_enrollment_id` FOREIGN KEY (`enrollment_id`) REFERENCES `enrollment` (`id`),
  CONSTRAINT `enrollment_detail_section_id_b8399fb7_fk_section_id` FOREIGN KEY (`section_id`) REFERENCES `section` (`id`),
  CONSTRAINT `ck_enrollment_detail_psu_grade` CHECK (((`final_grade` is null) or (`final_grade` in (1.00,1.25,1.50,1.75,2.00,2.25,2.50,2.75,3.00,4.00,5.00))))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `assessment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `assessed_at` datetime(6) NOT NULL,
  `total_amount` decimal(12,2) NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `remarks` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `enrollment_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `enrollment_id` (`enrollment_id`),
  CONSTRAINT `assessment_enrollment_id_f60c714c_fk_enrollment_id` FOREIGN KEY (`enrollment_id`) REFERENCES `enrollment` (`id`),
  CONSTRAINT `ck_assessment_total_non_negative` CHECK ((`total_amount` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `payment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `receipt_number` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payment_date` datetime(6) NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `method` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `assessment_id` int NOT NULL,
  `received_by_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_payment_receipt_number` (`receipt_number`),
  KEY `payment_assessment_id_af7b77ed_fk_assessment_id` (`assessment_id`),
  KEY `payment_received_by_id_db6d050c_fk_app_user_id` (`received_by_id`),
  CONSTRAINT `payment_assessment_id_af7b77ed_fk_assessment_id` FOREIGN KEY (`assessment_id`) REFERENCES `assessment` (`id`),
  CONSTRAINT `payment_received_by_id_db6d050c_fk_app_user_id` FOREIGN KEY (`received_by_id`) REFERENCES `app_user` (`id`),
  CONSTRAINT `ck_payment_amount_positive` CHECK ((`amount` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- End of simplified business schema. 15 tables.
