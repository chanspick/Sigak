-- ============================================================
-- user_history JSONB backfill — STEP 6
-- ============================================================
--
-- 실행 조건:
--   1. alembic upgrade head 완료 (20260502_userhistory revision 적용)
--   2. users.user_history JSONB + users.ig_last_snapshot_at 컬럼 존재
--
-- 실행 방법:
--   Railway DB console 또는 로컬 psql 로 이 파일 전체 실행.
--   트랜잭션 자동 커밋 모드 (BEGIN/COMMIT 블록 포함).
--
-- 안전성:
--   - user_history 는 jsonb_set 으로 partial update — 기존 값 보존.
--   - conversations / aspiration_analyses / best_shot_sessions / verdict_sessions
--     테이블이 없으면 해당 카테고리는 스킵 (DO block 예외 삼킴).
--   - ig_snapshot 은 NULL — backfill 시점엔 R2 저장 안 된 CDN URL 뿐.
--     STEP 2 이후 신규 세션부터 ig_snapshot 자동 연결됨.
--
-- ============================================================

BEGIN;

-- 0. 초기화 — 아직 null 인 row 만 {} 로 세팅
UPDATE users
SET user_history = '{}'::jsonb
WHERE user_history IS NULL;


-- 1. conversations 최근 10개씩 복사
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'conversations'
  ) THEN
    WITH ranked AS (
      SELECT
        user_id,
        id,
        started_at,
        ended_at,
        messages,
        ROW_NUMBER() OVER (
          PARTITION BY user_id ORDER BY started_at DESC NULLS LAST
        ) AS rn
      FROM conversations
    ),
    agg AS (
      SELECT
        user_id,
        jsonb_agg(
          jsonb_build_object(
            'session_id', id::text,
            'started_at', started_at,
            'ended_at', ended_at,
            'messages', COALESCE(messages, '[]'::jsonb),
            'ig_snapshot', NULL
          )
          ORDER BY started_at DESC NULLS LAST
        ) AS items
      FROM ranked
      WHERE rn <= 10
      GROUP BY user_id
    )
    UPDATE users u
    SET user_history = jsonb_set(
      COALESCE(u.user_history, '{}'::jsonb),
      '{conversations}',
      agg.items,
      true
    )
    FROM agg
    WHERE u.id = agg.user_id;

    RAISE NOTICE 'conversations backfill done';
  ELSE
    RAISE NOTICE 'conversations table absent — skipped';
  END IF;
END $$;


-- 2. aspiration_analyses 최근 10개씩 복사
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'aspiration_analyses'
  ) THEN
    WITH ranked AS (
      SELECT
        user_id,
        id,
        target_type,
        target_identifier,
        result_data,
        created_at,
        ROW_NUMBER() OVER (
          PARTITION BY user_id ORDER BY created_at DESC NULLS LAST
        ) AS rn
      FROM aspiration_analyses
    ),
    agg AS (
      SELECT
        user_id,
        jsonb_agg(
          jsonb_build_object(
            'analysis_id', id::text,
            'created_at', created_at,
            'source',
              CASE WHEN target_type = 'pinterest' THEN 'pinterest' ELSE 'instagram' END,
            'target_handle', target_identifier,
            'photo_pairs',
              COALESCE(result_data->'photo_pairs', '[]'::jsonb),
            'gap_narrative',
              COALESCE(result_data->>'gap_narrative', NULL),
            'sia_overall_message',
              COALESCE(result_data->>'sia_overall_message', NULL),
            'target_analysis_snapshot',
              COALESCE(result_data->'target_analysis_snapshot', NULL)
          )
          ORDER BY created_at DESC NULLS LAST
        ) AS items
      FROM ranked
      WHERE rn <= 10
      GROUP BY user_id
    )
    UPDATE users u
    SET user_history = jsonb_set(
      COALESCE(u.user_history, '{}'::jsonb),
      '{aspiration_analyses}',
      agg.items,
      true
    )
    FROM agg
    WHERE u.id = agg.user_id;

    RAISE NOTICE 'aspiration_analyses backfill done';
  ELSE
    RAISE NOTICE 'aspiration_analyses table absent — skipped';
  END IF;
END $$;


-- 3. best_shot_sessions (ready 상태만) 최근 10개씩 복사
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'best_shot_sessions'
  ) THEN
    WITH ranked AS (
      SELECT
        user_id,
        session_id,
        status,
        uploaded_count,
        result_data,
        created_at,
        ROW_NUMBER() OVER (
          PARTITION BY user_id ORDER BY created_at DESC NULLS LAST
        ) AS rn
      FROM best_shot_sessions
      WHERE status = 'ready'
    ),
    agg AS (
      SELECT
        user_id,
        jsonb_agg(
          jsonb_build_object(
            'session_id', session_id::text,
            'created_at', created_at,
            'uploaded_count', COALESCE(uploaded_count, 0),
            'uploaded_r2_dir',
              'users/' || user_id || '/best_shot/uploads/' || session_id::text || '/',
            'selected',
              COALESCE(result_data->'selected_photos', '[]'::jsonb),
            'overall_message',
              COALESCE(result_data->>'sia_overall_message', NULL)
          )
          ORDER BY created_at DESC NULLS LAST
        ) AS items
      FROM ranked
      WHERE rn <= 10
      GROUP BY user_id
    )
    UPDATE users u
    SET user_history = jsonb_set(
      COALESCE(u.user_history, '{}'::jsonb),
      '{best_shot_sessions}',
      agg.items,
      true
    )
    FROM agg
    WHERE u.id = agg.user_id;

    RAISE NOTICE 'best_shot_sessions backfill done';
  ELSE
    RAISE NOTICE 'best_shot_sessions table absent — skipped';
  END IF;
END $$;


-- 4. verdicts v2 최근 10개씩 복사 (full_unlocked 만)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'verdicts'
  ) THEN
    WITH ranked AS (
      SELECT
        user_id,
        id,
        version,
        full_unlocked,
        ranked_photo_ids,
        full_content,
        created_at,
        ROW_NUMBER() OVER (
          PARTITION BY user_id ORDER BY created_at DESC NULLS LAST
        ) AS rn
      FROM verdicts
      WHERE version = 'v2' AND full_unlocked = true
    ),
    agg AS (
      SELECT
        user_id,
        jsonb_agg(
          jsonb_build_object(
            'session_id', id::text,
            'created_at', created_at,
            'photos_r2_urls', COALESCE(ranked_photo_ids, '[]'::jsonb),
            'photo_insights',
              COALESCE(full_content->'photo_insights', '[]'::jsonb),
            'recommendation',
              COALESCE(full_content->'recommendation', NULL)
          )
          ORDER BY created_at DESC NULLS LAST
        ) AS items
      FROM ranked
      WHERE rn <= 10
      GROUP BY user_id
    )
    UPDATE users u
    SET user_history = jsonb_set(
      COALESCE(u.user_history, '{}'::jsonb),
      '{verdict_sessions}',
      agg.items,
      true
    )
    FROM agg
    WHERE u.id = agg.user_id;

    RAISE NOTICE 'verdicts backfill done';
  ELSE
    RAISE NOTICE 'verdicts table absent — skipped';
  END IF;
END $$;


-- 5. 검증 쿼리 (수동 확인용 — 커밋 전 결과 미리보기)
-- SELECT id,
--        jsonb_array_length(COALESCE(user_history->'conversations', '[]'::jsonb))        AS n_convos,
--        jsonb_array_length(COALESCE(user_history->'best_shot_sessions', '[]'::jsonb))   AS n_bs,
--        jsonb_array_length(COALESCE(user_history->'aspiration_analyses', '[]'::jsonb))  AS n_asp,
--        jsonb_array_length(COALESCE(user_history->'verdict_sessions', '[]'::jsonb))     AS n_verdict
-- FROM users
-- ORDER BY created_at DESC
-- LIMIT 20;

COMMIT;

-- ============================================================
-- Rollback (만약 필요 시):
--   UPDATE users SET user_history = '{}'::jsonb;
--   이후 신규 세션이 정상적으로 누적될 때까지 대기.
-- ============================================================
