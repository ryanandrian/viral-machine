# DB_SCHEMA_V2 — Introspeksi penuh (atliatnjhysdibmfypul)
> Auto-generated 2026-06-15. 39 tabel. SUMBER KEBENARAN struktur DB v2 (migrasi 0001-0043).

**Tabel:** admin_audit, ai_models, ai_providers, app_config, blog_posts, branding_config, channel_insights, channels, content_inventory, content_languages, demo_tours, direct_jobs, diversity_config, docs_articles, duration_presets, email_outbox, fonts, format_profiles, moods, music_library, niche_releases, niches, payments, pipeline_queue, pipeline_run_logs, plan_limits, pricing_audit, pricing_config, production_runs, production_schedules, support_messages, support_tickets, tenant_configs, tenant_credentials, tts_profiles, video_analytics, videos, voice_catalog, worker_heartbeats

## admin_audit  (rows=4, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- admin_uid text NOT NULL
- action text NOT NULL
- target_tenant text
- detail jsonb NOT NULL = '{}'::jsonb
- created_at timestamp with time zone NOT NULL = now()

## ai_models  (rows=7, RLS=ON)
- model_key text NOT NULL
- provider_key text NOT NULL
- component text NOT NULL
- model_id text NOT NULL
- display_name text NOT NULL
- quality_tier text NOT NULL = 'standard'::text
- cost_hint jsonb NOT NULL = '{}'::jsonb
- default_params jsonb NOT NULL = '{}'::jsonb
- is_active boolean NOT NULL = true
- sort_order integer NOT NULL = 100
- created_at timestamp with time zone NOT NULL = now()
- updated_at timestamp with time zone NOT NULL = now()
  - FK: FOREIGN KEY (provider_key) REFERENCES ai_providers(provider_key) ON DELETE RESTRICT
  - RLS: ai_models_read(r)

## ai_providers  (rows=3, RLS=ON)
- provider_key text NOT NULL
- display_name text NOT NULL
- adapter text NOT NULL
- base_url text
- auth_type text NOT NULL = 'api_key'::text
- request_param_schema jsonb NOT NULL = '{}'::jsonb
- is_active boolean NOT NULL = true
- created_at timestamp with time zone NOT NULL = now()
- updated_at timestamp with time zone NOT NULL = now()
  - RLS: ai_providers_read(r)

## app_config  (rows=1, RLS=ON)
- key text NOT NULL
- value integer NOT NULL
- description text
- updated_at timestamp with time zone = now()
  - RLS: app_config_read(r)

## blog_posts  (rows=6, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- slug text NOT NULL
- title text NOT NULL
- title_en text
- excerpt text
- excerpt_en text
- body text NOT NULL = ''::text
- body_en text
- category text
- cover text
- status text NOT NULL = 'draft'::text
- published_at timestamp with time zone
- sort_order integer NOT NULL = 100
- created_at timestamp with time zone NOT NULL = now()
- updated_at timestamp with time zone NOT NULL = now()
  - UNIQUE: UNIQUE (slug)
  - CHECK: CHECK ((status = ANY (ARRAY['draft'::text, 'published'::text])))
  - RLS: blog_public_read(r)

## branding_config  (rows=1, RLS=ON)
- id integer NOT NULL = 1
- logo_max_w_px integer = 220
- logo_min_w_px integer = 96
- logo_max_h_px integer = 220
- logo_min_h_px integer = 48
- logo_margin_px integer = 28
- logo_default_opacity numeric = 0.85
- updated_at timestamp with time zone = now()
  - CHECK: CHECK ((id = 1))
  - RLS: branding_config_read(r)

## channel_insights  (rows=18, RLS=ON)
- insight_id uuid NOT NULL = gen_random_uuid()
- tenant_id text NOT NULL
- channel_id character varying
- computed_at timestamp without time zone = now()
- videos_analyzed integer = 0
- niche_weights jsonb = '{}'::jsonb
- top_hooks jsonb = '[]'::jsonb
- content_type_perf jsonb = '{}'::jsonb
- avoid_patterns jsonb = '[]'::jsonb
- top_topics jsonb = '[]'::jsonb
- performance_grade character varying = 'insufficient_data'::character varying
- compliance jsonb = '{}'::jsonb
  - RLS: channel_insights_tenant_read(r)

## channels  (rows=2, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- tenant_id text NOT NULL
- channel_group text NOT NULL
- channel_name text NOT NULL
- platform text NOT NULL = 'youtube'::text
- platform_channel_id text
- token_path text NOT NULL = 'token_youtube.json'::text
- niche text NOT NULL = 'universe_mysteries'::text
- niche_mode text NOT NULL = 'fixed'::text
- niche_pool _text[] NOT NULL = ARRAY['universe_mysteries'::text]
- production_cron text
- publish_slots _text[]
- is_active boolean NOT NULL = true
- created_at timestamp with time zone NOT NULL = now()
- updated_at timestamp with time zone NOT NULL = now()
- duration_preset integer
- format_profile text
- landing_link text
- link_position text = 'bottom'::text
- cta_mode text = 'implicit'::text
- brand_name text
- brand_cta_text text
- brand_logo text
- logo_position text = 'top-right'::text
- logo_size numeric = 0.12
- logo_opacity numeric = 0.85
- publish_privacy text = 'private'::text
- ai_disclosure boolean = true
- content_language text
  - FK: FOREIGN KEY (tenant_id) REFERENCES tenant_configs(tenant_id) ON DELETE CASCADE
  - CHECK: CHECK ((niche_mode = ANY (ARRAY['fixed'::text, 'random'::text])))
  - CHECK: CHECK ((platform = ANY (ARRAY['youtube'::text, 'tiktok'::text, 'instagram'::text])))
  - RLS: channels_tenant_read(r), channels_tenant_update(w), channels_tenant_insert(a)

## content_inventory  (rows=0, RLS=ON)
- id bigint NOT NULL = nextval('content_inventory_id_seq'::regc
- tenant_id text NOT NULL
- channel_id text
- niche text
- s3_key text
- status text NOT NULL = 'producing'::text
- metadata jsonb NOT NULL = '{}'::jsonb
- produced_at timestamp with time zone
- target_slot timestamp with time zone
- expires_at timestamp with time zone
- created_at timestamp with time zone NOT NULL = now()
- updated_at timestamp with time zone NOT NULL = now()
  - RLS: content_inventory_tenant_read(r)

## content_languages  (rows=6, RLS=ON)
- locale text NOT NULL
- display_name text NOT NULL
- tts_providers_supported jsonb NOT NULL = '[]'::jsonb
- quality_tier text NOT NULL = 'experimental'::text
- caption_font text
- is_active boolean NOT NULL = false
- sort_order integer NOT NULL = 100
- updated_at timestamp with time zone NOT NULL = now()
  - RLS: content_languages_read(r)

## demo_tours  (rows=4, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- label text NOT NULL
- label_en text
- href text NOT NULL
- heading text
- heading_en text
- caption text
- caption_en text
- bullets jsonb NOT NULL = '[]'::jsonb
- bullets_en jsonb NOT NULL = '[]'::jsonb
- is_active boolean NOT NULL = true
- sort_order integer NOT NULL = 100
- updated_at timestamp with time zone NOT NULL = now()
  - RLS: demo_public_read(r)

## direct_jobs  (rows=1, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- tenant_id text NOT NULL
- channel_id text NOT NULL
- job_type text NOT NULL = 'test'::text
- niche text
- source_run_id text
- publish_privacy text NOT NULL = 'private'::text
- status text NOT NULL = 'pending'::text
- run_id text
- error text
- requested_by text
- created_at timestamp with time zone NOT NULL = now()
- started_at timestamp with time zone
- completed_at timestamp with time zone
  - CHECK: CHECK ((status = ANY (ARRAY['pending'::text, 'producing'::text, 'published'::text, 'failed'::text])))
  - CHECK: CHECK ((job_type = ANY (ARRAY['test'::text, 'retry'::text, 'admin_test'::text])))
  - RLS: direct_jobs_tenant_insert(a), direct_jobs_tenant_read(r)

## diversity_config  (rows=1, RLS=ON)
- id integer NOT NULL = 1
- lookback_window integer = 6
- voice_rotation_enabled boolean = true
- hook_rotation_enabled boolean = true
- music_rotation_enabled boolean = true
- visual_rotation_enabled boolean = true
- hook_pattern_pool jsonb = '["question", "impossible_claim", "you_d
- updated_at timestamp with time zone = now()
  - CHECK: CHECK ((id = 1))
  - RLS: diversity_config_read(r)

## docs_articles  (rows=14, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- slug text NOT NULL
- grp text NOT NULL = 'Lainnya'::text
- grp_en text
- title text NOT NULL
- title_en text
- body text NOT NULL = ''::text
- body_en text
- status text NOT NULL = 'draft'::text
- sort_order integer NOT NULL = 100
- created_at timestamp with time zone NOT NULL = now()
- updated_at timestamp with time zone NOT NULL = now()
  - CHECK: CHECK ((status = ANY (ARRAY['draft'::text, 'published'::text])))
  - UNIQUE: UNIQUE (slug)
  - RLS: docs_public_read(r)

## duration_presets  (rows=7, RLS=ON)
- seconds integer NOT NULL
- visual_beats integer NOT NULL
- render_mode text = 'image_sequence'::text
- notes text
- is_active boolean = true
- updated_at timestamp with time zone = now()
- is_default boolean = false
  - RLS: duration_presets_read(r)

## email_outbox  (rows=0, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- tenant_id text NOT NULL
- subject text NOT NULL
- body text NOT NULL
- status text NOT NULL = 'pending'::text
- created_by text
- created_at timestamp with time zone NOT NULL = now()
- sent_at timestamp with time zone
- error text
  - CHECK: CHECK ((status = ANY (ARRAY['pending'::text, 'sent'::text, 'failed'::text])))

## fonts  (rows=1, RLS=ON)
- id integer NOT NULL = nextval('fonts_id_seq'::regclass)
- name character varying NOT NULL
- file_name character varying NOT NULL
- preview_url character varying = ''::character varying
- is_active boolean = true
- created_at timestamp with time zone = now()
  - UNIQUE: UNIQUE (name)
  - RLS: fonts_select_anon(r)

## format_profiles  (rows=4, RLS=ON)
- format_key text NOT NULL
- name text NOT NULL
- section_template jsonb = '[]'::jsonb
- default_wps numeric NOT NULL
- default_cta_mode text = 'implicit'::text
- render_mode text = 'image_sequence'::text
- is_active boolean = true
- updated_at timestamp with time zone = now()
  - RLS: format_profiles_read(r)

## moods  (rows=15, RLS=OFF)
- mood_id text NOT NULL
- name text NOT NULL
- keywords jsonb = '[]'::jsonb
- is_active boolean = true
- created_at timestamp with time zone = now()

## music_library  (rows=28, RLS=OFF)
- id uuid NOT NULL = gen_random_uuid()
- tenant_id text
- niche text NOT NULL
- mood text NOT NULL
- name text NOT NULL
- r2_key text NOT NULL
- duration_s integer
- bpm integer
- source text = 'pixabay'::text
- is_active boolean = true
- is_default boolean = false
- play_count integer = 0
- pixabay_id text
- created_at timestamp with time zone = now()
- updated_at timestamp with time zone = now()

## niche_releases  (rows=0, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- niche_id character varying NOT NULL
- scheduled_at timestamp with time zone NOT NULL
- announced boolean NOT NULL = false
- status text NOT NULL = 'scheduled'::text
- created_by text
- created_at timestamp with time zone NOT NULL = now()
  - FK: FOREIGN KEY (niche_id) REFERENCES niches(niche_id) ON DELETE CASCADE

## niches  (rows=4, RLS=OFF)
- niche_id character varying NOT NULL
- name character varying NOT NULL
- keywords jsonb NOT NULL = '[]'::jsonb
- style character varying = ''::character varying
- target_emotion character varying = ''::character varying
- hook_templates jsonb = '[]'::jsonb
- default_hashtags jsonb = '[]'::jsonb
- is_active boolean = true
- created_at timestamp without time zone = now()
- visual_style jsonb = '{}'::jsonb
- visual_fallbacks jsonb = '[]'::jsonb
- mood_priority jsonb = '[]'::jsonb
- voice_profile jsonb = '{}'::jsonb
- emotion_scoring_criteria text = ''::text
- section_timing jsonb
- image_quality_tags text
- image_negative_prompt text
- is_base boolean = false
- access_type text NOT NULL = 'public'::text
- exclusive_to text
- exclusive_until timestamp with time zone
- released_at timestamp with time zone
- release_scheduled_at timestamp with time zone
  - CHECK: CHECK ((access_type = ANY (ARRAY['public'::text, 'pending'::text, 'private'::text])))

## payments  (rows=0, RLS=ON)
- order_id text NOT NULL
- tenant_id text NOT NULL
- plan_type text
- gross_amount integer NOT NULL
- currency text = 'IDR'::text
- status text = 'pending'::text
- payment_type text
- snap_token text
- fraud_status text
- period_start timestamp with time zone
- period_end timestamp with time zone
- raw_notification jsonb
- created_at timestamp with time zone = now()
- updated_at timestamp with time zone = now()
  - RLS: payments_tenant_read(r)

## pipeline_queue  (rows=101, RLS=ON)
- id bigint NOT NULL = nextval('pipeline_queue_id_seq'::regclas
- tenant_id text NOT NULL
- scheduled_at timestamp with time zone NOT NULL = now()
- started_at timestamp with time zone
- completed_at timestamp with time zone
- status text NOT NULL = 'pending'::text
- job_type text NOT NULL = 'production'::text
- error_message text
- created_at timestamp with time zone NOT NULL = now()
- channel_id text
  - RLS: pipeline_queue_tenant_read(r)

## pipeline_run_logs  (rows=0, RLS=ON)
- id bigint NOT NULL = nextval('pipeline_run_logs_id_seq'::regc
- tenant_id text NOT NULL
- channel_id text
- queue_id text
- run_id text
- level text NOT NULL = 'INFO'::text
- step text
- category text
- message text NOT NULL
- metadata jsonb NOT NULL = '{}'::jsonb
- created_at timestamp with time zone NOT NULL = now()
  - RLS: pipeline_run_logs_tenant_read(r)

## plan_limits  (rows=4, RLS=ON)
- plan_type text NOT NULL
- max_videos_per_day integer NOT NULL = 1
- max_channels integer NOT NULL = 1
  - RLS: plan_limits_read(r)

## pricing_audit  (rows=0, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- key text NOT NULL
- old_value jsonb
- new_value jsonb NOT NULL
- changed_by text
- changed_at timestamp with time zone NOT NULL = now()

## pricing_config  (rows=9, RLS=ON)
- key text NOT NULL
- value_idr integer NOT NULL
- value_usd_cents integer
- description text
- category text
- active boolean NOT NULL = true
- effective_from timestamp with time zone NOT NULL = now()
- effective_until timestamp with time zone
- updated_by text
- updated_at timestamp with time zone NOT NULL = now()
  - RLS: pricing_config_read(r)

## production_runs  (rows=99, RLS=ON)
- id bigint NOT NULL = nextval('production_runs_id_seq'::regcla
- queue_id bigint
- tenant_id text NOT NULL
- run_id text
- topic text
- niche text
- viral_score numeric
- llm_provider text
- status text
- youtube_url text
- youtube_video_id text
- elapsed_seconds numeric
- qc_passed boolean
- error_message text
- run_metadata jsonb
- created_at timestamp with time zone NOT NULL = now()
- channel_id text
  - FK: FOREIGN KEY (queue_id) REFERENCES pipeline_queue(id)
  - RLS: production_runs_tenant_read(r)

## production_schedules  (rows=5, RLS=ON)
- schedule_id uuid NOT NULL = gen_random_uuid()
- channel_id character varying NOT NULL
- tenant_id text NOT NULL
- cron_expression character varying NOT NULL
- niche_id character varying
- niche_focus text
- is_active boolean = true
- created_at timestamp without time zone = now()
- content_type character varying = 'short'::character varying
  - FK: FOREIGN KEY (niche_id) REFERENCES niches(niche_id)
  - RLS: production_schedules_tenant_insert(a), production_schedules_tenant_read(r), production_schedules_tenant_update(w)

## support_messages  (rows=0, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- ticket_id uuid NOT NULL
- sender text NOT NULL
- body text NOT NULL
- created_at timestamp with time zone NOT NULL = now()
  - CHECK: CHECK ((sender = ANY (ARRAY['tenant'::text, 'admin'::text])))
  - FK: FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE
  - RLS: support_messages_tenant_insert(a), support_messages_tenant_read(r)

## support_tickets  (rows=0, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- tenant_id text NOT NULL
- subject text NOT NULL
- status text NOT NULL = 'open'::text
- priority text NOT NULL = 'normal'::text
- assigned_to text
- created_at timestamp with time zone NOT NULL = now()
- updated_at timestamp with time zone NOT NULL = now()
  - CHECK: CHECK ((status = ANY (ARRAY['open'::text, 'pending'::text, 'resolved'::text])))
  - RLS: support_tickets_tenant_insert(a), support_tickets_tenant_read(r)

## tenant_configs  (rows=2, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- tenant_id text NOT NULL
- tts_provider text = 'edge_tts'::text
- tts_voice text = 'en-US-GuyNeural'::text
- tts_api_key text  ⚠️ DEPRECATED-plaintext (migr 0044) → pakai tts_api_key_enc; di-null pasca-migrasi
- tts_api_key_enc text  ← Fernet (migr 0044); tulis via vault /api/keys/set; baca via _eff_key
- visual_provider text = 'pexels'::text
- visual_max_clip_mb integer = 50
- visual_api_key text  ⚠️ DEPRECATED-plaintext (migr 0044) → visual_api_key_enc
- visual_api_key_enc text  ← Fernet (migr 0044)
- visual_ai_model text
- llm_provider text = 'openai'::text
- llm_model text = 'gpt-4o-mini'::text
- llm_api_key text  ⚠️ DEPRECATED-plaintext (migr 0044) → llm_api_key_enc
- llm_api_key_enc text  ← Fernet (migr 0044)
- youtube_api_key_enc text  ← Fernet (migr 0044; pasangan youtube_api_key plaintext di bawah)
- niche text = 'universe_mysteries'::text
- videos_per_day integer = 1
- publish_platforms _text[] = '{youtube}'::text[]
- production_cron text = '0 1 * * *'::text
- analytics_cron text = '0 13 * * *'::text
- created_at timestamp with time zone = now()
- updated_at timestamp with time zone = now()
- plan_type text = 'starter'::text
- max_videos_per_day integer = 1
- publish_slots _text[] = '{13:00}'::text[]
- peak_region text = 'us'::text
- auto_schedule boolean = true
- is_developer boolean = false
- discount_pct integer = 0
- visual_mode text = 'video'::text
- tts_voice_per_niche jsonb = '{"fun_facts": "21m00Tcm4TlvDq8ikWAM", "
- script_min_viral_score integer = 80
- script_max_retry integer = 3
- music_enabled boolean = false
- caption_style jsonb = '{"margin_v": 380, "font_size": 68, "max
- music_volume double precision = 0.18
- tts_voice_settings jsonb = '{"fun_facts": {"speed": 0.90, "style": 
- niche_mode text = 'fixed'::text
- niche_pool _text[] = ARRAY['universe_mysteries'::text]
- duplicate_lookback_days integer NOT NULL = 30
- tts_fallback_provider text NOT NULL = 'edge_tts'::text
- visual_fallback_mode text NOT NULL = 'video'::text
- llm_script_fallback text NOT NULL = 'gpt-4o-mini'::text
- production_on_api_error text NOT NULL = 'fallback'::text
- channel_group text NOT NULL = 'default'::text
- trailing_silence double precision NOT NULL = 2.5
- thumbnail_enabled boolean NOT NULL = true
- thumbnail_source text NOT NULL = 'ai_generate'::text
- hook_title_style jsonb NOT NULL = '{"shadow": 3, "enabled": true, "outline
- niche_hashtags jsonb NOT NULL = '{"fun_facts": ["#FunFacts", "#MindBlown
- telegram_chat_id text
- telegram_notify_enabled boolean NOT NULL = true
- telegram_enabled boolean = true
- channel_name character varying = ''::character varying
- loop_ending_enabled boolean = true
- loop_ending_duration double precision = 1.5
- default_niche_rotation jsonb = '[]'::jsonb
- niche_rotation_index integer = 0
- youtube_api_key character varying
- viral_score_weights jsonb = '{}'::jsonb
- image_quality character varying = 'low'::character varying
- is_active boolean NOT NULL = true
- timezone text NOT NULL = 'UTC'::text
- llm_library text
- llm_models jsonb
- niche_fallback text
- music_default_mood text
- display_handle text
- subscription_status text = 'active'::text
- current_period_end timestamp with time zone
- trial_started_at timestamp with time zone
  - CHECK: CHECK ((production_on_api_error = ANY (ARRAY['fallback'::text, 'stop_and_notify'::text])))
  - CHECK: CHECK ((thumbnail_source = ANY (ARRAY['ai_generate'::text, 'hook_frame'::text])))
  - UNIQUE: UNIQUE (tenant_id)
  - RLS: tenant_configs_tenant_read(r)

## tenant_credentials  (rows=1, RLS=ON)
- tenant_id text NOT NULL
- google_client_id text
- google_client_secret_enc text
- google_refresh_token_enc text
- google_access_token_enc text
- token_expiry timestamp with time zone
- channel_id text
- scopes jsonb NOT NULL = '[]'::jsonb
- created_at timestamp with time zone NOT NULL = now()
- updated_at timestamp with time zone NOT NULL = now()

## tts_profiles  (rows=3, RLS=ON)
- provider_key text NOT NULL
- tts_class text NOT NULL
- delivery_wps numeric NOT NULL
- has_word_timeframe boolean = false
- speed_param text
- is_active boolean = true
- updated_at timestamp with time zone = now()
  - RLS: tts_profiles_read(r)

## video_analytics  (rows=3182, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- video_id text NOT NULL
- tenant_id text NOT NULL
- platform text NOT NULL
- views bigint = 0
- likes bigint = 0
- comments bigint = 0
- shares bigint = 0
- collected_at timestamp with time zone = now()
- niche character varying
- title text
- hook_text text
- watch_time_mins integer = 0
- avg_view_pct double precision = 0
- ctr double precision = 0
- subscriber_gain integer = 0
- has_full_analytics boolean = false
- published_at timestamp without time zone
- channel_id character varying
- content_type character varying
- views_per_sub double precision = 0
- analytics_date date = CURRENT_DATE
- fetched_at timestamp without time zone = now()
  - RLS: video_analytics_tenant_read(r)

## videos  (rows=212, RLS=ON)
- id uuid NOT NULL = gen_random_uuid()
- tenant_id text NOT NULL
- run_id text NOT NULL
- platform text NOT NULL
- video_id text
- url text
- title text
- hook text
- niche text
- viral_score double precision
- status text = 'published'::text
- published_at timestamp with time zone = now()
- created_at timestamp with time zone = now()
- topic text
- topic_slug text
- channel_id uuid
- qc_passed boolean
- qc_reason text
- duration_secs double precision
- file_size_mb double precision
- topic_scores jsonb = '{}'::jsonb
- insights_grade character varying = ''::character varying
- voice_id text
- hook_pattern text
- music_mood text
- visual_seed bigint
  - CHECK: CHECK ((status = ANY (ARRAY['published'::text, 'qc_failed'::text, 'failed'::text])))
  - FK: FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE SET NULL
  - RLS: videos_tenant_read(r)

## voice_catalog  (rows=0, RLS=ON)
- voice_key text NOT NULL
- provider_key text NOT NULL
- display_name text NOT NULL
- locale text
- gender text
- niche_default text
- preview_url text
- is_active boolean NOT NULL = true
- sort_order integer NOT NULL = 100
- updated_at timestamp with time zone NOT NULL = now()
  - RLS: voice_catalog_read(r)

## worker_heartbeats  (rows=0, RLS=ON)
- worker_name text NOT NULL
- status text NOT NULL = 'up'::text
- current_job text
- node text
- last_heartbeat_at timestamp with time zone NOT NULL = now()
