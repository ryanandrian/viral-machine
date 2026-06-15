# DB_SCHEMA_V2 — Introspeksi penuh (atliatnjhysdibmfypul, Singapore)
> Auto-generated 2026-06-15 via psycopg2. 27 tabel, 0 view. SUMBER KEBENARAN struktur DB v2.

**Tabel:** ai_models, ai_providers, app_config, branding_config, channel_insights, channels, content_inventory, content_languages, diversity_config, duration_presets, fonts, format_profiles, moods, music_library, niches, payments, pipeline_queue, pipeline_run_logs, plan_limits, pricing_config, production_runs, production_schedules, tenant_configs, tenant_credentials, tts_profiles, video_analytics, videos

## Enums
(none)

## ai_models  (rows=7, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| model_key | text | N |  |
| provider_key | text | N |  |
| component | text | N |  |
| model_id | text | N |  |
| display_name | text | N |  |
| quality_tier | text | N | 'standard'::text |
| cost_hint | jsonb | N | '{}'::jsonb |
| default_params | jsonb | N | '{}'::jsonb |
| is_active | boolean | N | true |
| sort_order | integer | N | 100 |
| created_at | timestamp with time zone | N | now() |
| updated_at | timestamp with time zone | N | now() |

**Constraints:**
- FK `ai_models_provider_key_fkey`: FOREIGN KEY (provider_key) REFERENCES ai_providers(provider_key) ON DELETE RESTRICT
- PK `ai_models_pkey`: PRIMARY KEY (model_key)

**Indexes:**
- public.ai_models USING btree (model_key)
- public.ai_models USING btree (component) WHERE is_active
- public.ai_models USING btree (provider_key)

**RLS policies:**
- `ai_models_read` SELECT roles={-} USING(true) WITH CHECK(None)

## ai_providers  (rows=3, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| provider_key | text | N |  |
| display_name | text | N |  |
| adapter | text | N |  |
| base_url | text | Y |  |
| auth_type | text | N | 'api_key'::text |
| request_param_schema | jsonb | N | '{}'::jsonb |
| is_active | boolean | N | true |
| created_at | timestamp with time zone | N | now() |
| updated_at | timestamp with time zone | N | now() |

**Constraints:**
- PK `ai_providers_pkey`: PRIMARY KEY (provider_key)

**Indexes:**
- public.ai_providers USING btree (provider_key)

**RLS policies:**
- `ai_providers_read` SELECT roles={-} USING(true) WITH CHECK(None)

## app_config  (rows=1, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| key | text | N |  |
| value | integer | N |  |
| description | text | Y |  |
| updated_at | timestamp with time zone | Y | now() |

**Constraints:**
- PK `app_config_pkey`: PRIMARY KEY (key)

**Indexes:**
- public.app_config USING btree (key)

**RLS policies:**
- `app_config_read` SELECT roles={-} USING(true) WITH CHECK(None)

## branding_config  (rows=1, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | integer | N | 1 |
| logo_max_w_px | integer | Y | 220 |
| logo_min_w_px | integer | Y | 96 |
| logo_max_h_px | integer | Y | 220 |
| logo_min_h_px | integer | Y | 48 |
| logo_margin_px | integer | Y | 28 |
| logo_default_opacity | numeric | Y | 0.85 |
| updated_at | timestamp with time zone | Y | now() |

**Constraints:**
- CHECK `branding_config_single_row`: CHECK ((id = 1))
- PK `branding_config_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.branding_config USING btree (id)

**RLS policies:**
- `branding_config_read` SELECT roles={-} USING(true) WITH CHECK(None)

## channel_insights  (rows=18, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| insight_id | uuid | N | gen_random_uuid() |
| tenant_id | text | N |  |
| channel_id | character varying | Y |  |
| computed_at | timestamp without time zone | Y | now() |
| videos_analyzed | integer | Y | 0 |
| niche_weights | jsonb | Y | '{}'::jsonb |
| top_hooks | jsonb | Y | '[]'::jsonb |
| content_type_perf | jsonb | Y | '{}'::jsonb |
| avoid_patterns | jsonb | Y | '[]'::jsonb |
| top_topics | jsonb | Y | '[]'::jsonb |
| performance_grade | character varying | Y | 'insufficient_data'::character varying |
| compliance | jsonb | Y | '{}'::jsonb |

**Constraints:**
- PK `channel_insights_pkey`: PRIMARY KEY (insight_id)

**Indexes:**
- public.channel_insights USING btree (insight_id)
- public.channel_insights USING btree (tenant_id, computed_at DESC)
- public.channel_insights USING btree (tenant_id)

**RLS policies:**
- `channel_insights_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)

## channels  (rows=1, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | uuid | N | gen_random_uuid() |
| tenant_id | text | N |  |
| channel_group | text | N |  |
| channel_name | text | N |  |
| platform | text | N | 'youtube'::text |
| platform_channel_id | text | Y |  |
| token_path | text | N | 'token_youtube.json'::text |
| niche | text | N | 'universe_mysteries'::text |
| niche_mode | text | N | 'fixed'::text |
| niche_pool | _text[] | N | ARRAY['universe_mysteries'::text] |
| production_cron | text | Y |  |
| publish_slots | _text[] | Y |  |
| is_active | boolean | N | true |
| created_at | timestamp with time zone | N | now() |
| updated_at | timestamp with time zone | N | now() |
| duration_preset | integer | Y |  |
| format_profile | text | Y |  |
| landing_link | text | Y |  |
| link_position | text | Y | 'bottom'::text |
| cta_mode | text | Y | 'implicit'::text |
| brand_name | text | Y |  |
| brand_cta_text | text | Y |  |
| brand_logo | text | Y |  |
| logo_position | text | Y | 'top-right'::text |
| logo_size | numeric | Y | 0.12 |
| logo_opacity | numeric | Y | 0.85 |
| publish_privacy | text | Y | 'private'::text |
| ai_disclosure | boolean | Y | true |
| content_language | text | Y |  |

**Constraints:**
- CHECK `chk_niche_mode`: CHECK ((niche_mode = ANY (ARRAY['fixed'::text, 'random'::text])))
- CHECK `chk_platform`: CHECK ((platform = ANY (ARRAY['youtube'::text, 'tiktok'::text, 'instagram'::text])))
- FK `channels_tenant_id_fkey`: FOREIGN KEY (tenant_id) REFERENCES tenant_configs(tenant_id) ON DELETE CASCADE
- PK `channels_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.channels USING btree (id)
- public.channels USING btree (channel_group)
- public.channels USING btree (platform, is_active)
- public.channels USING btree (tenant_id)

**RLS policies:**
- `channels_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)
- `channels_tenant_update` UPDATE roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK((tenant_id = (auth.uid())::text))
- `channels_tenant_insert` INSERT roles={-} USING(None) WITH CHECK((tenant_id = (auth.uid())::text))

## content_inventory  (rows=0, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | bigint | N | nextval('content_inventory_id_seq'::regclass) |
| tenant_id | text | N |  |
| channel_id | text | Y |  |
| niche | text | Y |  |
| s3_key | text | Y |  |
| status | text | N | 'producing'::text |
| metadata | jsonb | N | '{}'::jsonb |
| produced_at | timestamp with time zone | Y |  |
| target_slot | timestamp with time zone | Y |  |
| expires_at | timestamp with time zone | Y |  |
| created_at | timestamp with time zone | N | now() |
| updated_at | timestamp with time zone | N | now() |

**Constraints:**
- PK `content_inventory_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.content_inventory USING btree (id)
- public.content_inventory USING btree (channel_id, status)
- public.content_inventory USING btree (status, target_slot) WHERE (status = 'ready'::text)
- public.content_inventory USING btree (tenant_id)

**RLS policies:**
- `content_inventory_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)

## content_languages  (rows=6, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| locale | text | N |  |
| display_name | text | N |  |
| tts_providers_supported | jsonb | N | '[]'::jsonb |
| quality_tier | text | N | 'experimental'::text |
| caption_font | text | Y |  |
| is_active | boolean | N | false |
| sort_order | integer | N | 100 |
| updated_at | timestamp with time zone | N | now() |

**Constraints:**
- PK `content_languages_pkey`: PRIMARY KEY (locale)

**Indexes:**
- public.content_languages USING btree (locale)

**RLS policies:**
- `content_languages_read` SELECT roles={-} USING(true) WITH CHECK(None)

## diversity_config  (rows=1, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | integer | N | 1 |
| lookback_window | integer | Y | 6 |
| voice_rotation_enabled | boolean | Y | true |
| hook_rotation_enabled | boolean | Y | true |
| music_rotation_enabled | boolean | Y | true |
| visual_rotation_enabled | boolean | Y | true |
| hook_pattern_pool | jsonb | Y | '["question", "impossible_claim", "you_dont_know", |
| updated_at | timestamp with time zone | Y | now() |

**Constraints:**
- CHECK `diversity_config_single_row`: CHECK ((id = 1))
- PK `diversity_config_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.diversity_config USING btree (id)

**RLS policies:**
- `diversity_config_read` SELECT roles={-} USING(true) WITH CHECK(None)

## duration_presets  (rows=7, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| seconds | integer | N |  |
| visual_beats | integer | N |  |
| render_mode | text | Y | 'image_sequence'::text |
| notes | text | Y |  |
| is_active | boolean | Y | true |
| updated_at | timestamp with time zone | Y | now() |
| is_default | boolean | Y | false |

**Constraints:**
- PK `duration_presets_pkey`: PRIMARY KEY (seconds)

**Indexes:**
- public.duration_presets USING btree (seconds)

**RLS policies:**
- `duration_presets_read` SELECT roles={-} USING(true) WITH CHECK(None)

## fonts  (rows=1, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | integer | N | nextval('fonts_id_seq'::regclass) |
| name | character varying | N |  |
| file_name | character varying | N |  |
| preview_url | character varying | Y | ''::character varying |
| is_active | boolean | Y | true |
| created_at | timestamp with time zone | Y | now() |

**Constraints:**
- PK `fonts_pkey`: PRIMARY KEY (id)
- UNIQUE `fonts_name_key`: UNIQUE (name)

**Indexes:**
- public.fonts USING btree (name)
- public.fonts USING btree (id)

**RLS policies:**
- `fonts_select_anon` SELECT roles={-} USING(true) WITH CHECK(None)

## format_profiles  (rows=4, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| format_key | text | N |  |
| name | text | N |  |
| section_template | jsonb | Y | '[]'::jsonb |
| default_wps | numeric | N |  |
| default_cta_mode | text | Y | 'implicit'::text |
| render_mode | text | Y | 'image_sequence'::text |
| is_active | boolean | Y | true |
| updated_at | timestamp with time zone | Y | now() |

**Constraints:**
- PK `format_profiles_pkey`: PRIMARY KEY (format_key)

**Indexes:**
- public.format_profiles USING btree (format_key)

**RLS policies:**
- `format_profiles_read` SELECT roles={-} USING(true) WITH CHECK(None)

## moods  (rows=15, RLS=OFF)
| col | type | null | default |
|---|---|---|---|
| mood_id | text | N |  |
| name | text | N |  |
| keywords | jsonb | Y | '[]'::jsonb |
| is_active | boolean | Y | true |
| created_at | timestamp with time zone | Y | now() |

**Constraints:**
- PK `moods_pkey`: PRIMARY KEY (mood_id)

**Indexes:**
- public.moods USING btree (mood_id)

## music_library  (rows=28, RLS=OFF)
| col | type | null | default |
|---|---|---|---|
| id | uuid | N | gen_random_uuid() |
| tenant_id | text | Y |  |
| niche | text | N |  |
| mood | text | N |  |
| name | text | N |  |
| r2_key | text | N |  |
| duration_s | integer | Y |  |
| bpm | integer | Y |  |
| source | text | Y | 'pixabay'::text |
| is_active | boolean | Y | true |
| is_default | boolean | Y | false |
| play_count | integer | Y | 0 |
| pixabay_id | text | Y |  |
| created_at | timestamp with time zone | Y | now() |
| updated_at | timestamp with time zone | Y | now() |

**Constraints:**
- PK `music_library_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.music_library USING btree (niche, mood, is_active)
- public.music_library USING btree (tenant_id, is_active)
- public.music_library USING btree (id)

## niches  (rows=4, RLS=OFF)
| col | type | null | default |
|---|---|---|---|
| niche_id | character varying | N |  |
| name | character varying | N |  |
| keywords | jsonb | N | '[]'::jsonb |
| style | character varying | Y | ''::character varying |
| target_emotion | character varying | Y | ''::character varying |
| hook_templates | jsonb | Y | '[]'::jsonb |
| default_hashtags | jsonb | Y | '[]'::jsonb |
| is_active | boolean | Y | true |
| created_at | timestamp without time zone | Y | now() |
| visual_style | jsonb | Y | '{}'::jsonb |
| visual_fallbacks | jsonb | Y | '[]'::jsonb |
| mood_priority | jsonb | Y | '[]'::jsonb |
| voice_profile | jsonb | Y | '{}'::jsonb |
| emotion_scoring_criteria | text | Y | ''::text |
| section_timing | jsonb | Y |  |
| image_quality_tags | text | Y |  |
| image_negative_prompt | text | Y |  |
| is_base | boolean | Y | false |

**Constraints:**
- PK `niches_pkey`: PRIMARY KEY (niche_id)

**Indexes:**
- public.niches USING btree (niche_id)

## payments  (rows=0, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| order_id | text | N |  |
| tenant_id | text | N |  |
| plan_type | text | Y |  |
| gross_amount | integer | N |  |
| currency | text | Y | 'IDR'::text |
| status | text | Y | 'pending'::text |
| payment_type | text | Y |  |
| snap_token | text | Y |  |
| fraud_status | text | Y |  |
| period_start | timestamp with time zone | Y |  |
| period_end | timestamp with time zone | Y |  |
| raw_notification | jsonb | Y |  |
| created_at | timestamp with time zone | Y | now() |
| updated_at | timestamp with time zone | Y | now() |

**Constraints:**
- PK `payments_pkey`: PRIMARY KEY (order_id)

**Indexes:**
- public.payments USING btree (tenant_id, created_at DESC)
- public.payments USING btree (order_id)

**RLS policies:**
- `payments_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)

## pipeline_queue  (rows=101, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | bigint | N | nextval('pipeline_queue_id_seq'::regclass) |
| tenant_id | text | N |  |
| scheduled_at | timestamp with time zone | N | now() |
| started_at | timestamp with time zone | Y |  |
| completed_at | timestamp with time zone | Y |  |
| status | text | N | 'pending'::text |
| job_type | text | N | 'production'::text |
| error_message | text | Y |  |
| created_at | timestamp with time zone | N | now() |
| channel_id | text | Y |  |

**Constraints:**
- PK `pipeline_queue_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.pipeline_queue USING btree (status)
- public.pipeline_queue USING btree (tenant_id)
- public.pipeline_queue USING btree (id)

**RLS policies:**
- `pipeline_queue_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)

## pipeline_run_logs  (rows=0, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | bigint | N | nextval('pipeline_run_logs_id_seq'::regclass) |
| tenant_id | text | N |  |
| channel_id | text | Y |  |
| queue_id | text | Y |  |
| run_id | text | Y |  |
| level | text | N | 'INFO'::text |
| step | text | Y |  |
| category | text | Y |  |
| message | text | N |  |
| metadata | jsonb | N | '{}'::jsonb |
| created_at | timestamp with time zone | N | now() |

**Constraints:**
- PK `pipeline_run_logs_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.pipeline_run_logs USING btree (level) WHERE (level <> 'INFO'::text)
- public.pipeline_run_logs USING btree (run_id)
- public.pipeline_run_logs USING btree (tenant_id, created_at DESC)
- public.pipeline_run_logs USING btree (id)

**RLS policies:**
- `pipeline_run_logs_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)

## plan_limits  (rows=4, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| plan_type | text | N |  |
| max_videos_per_day | integer | N | 1 |
| max_channels | integer | N | 1 |

**Constraints:**
- PK `plan_limits_pkey`: PRIMARY KEY (plan_type)

**Indexes:**
- public.plan_limits USING btree (plan_type)

**RLS policies:**
- `plan_limits_read` SELECT roles={-} USING(true) WITH CHECK(None)

## pricing_config  (rows=9, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| key | text | N |  |
| value_idr | integer | N |  |
| value_usd_cents | integer | Y |  |
| description | text | Y |  |
| category | text | Y |  |
| active | boolean | N | true |
| effective_from | timestamp with time zone | N | now() |
| effective_until | timestamp with time zone | Y |  |
| updated_by | text | Y |  |
| updated_at | timestamp with time zone | N | now() |

**Constraints:**
- PK `pricing_config_pkey`: PRIMARY KEY (key)

**Indexes:**
- public.pricing_config USING btree (key)

**RLS policies:**
- `pricing_config_read` SELECT roles={-} USING(true) WITH CHECK(None)

## production_runs  (rows=99, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | bigint | N | nextval('production_runs_id_seq'::regclass) |
| queue_id | bigint | Y |  |
| tenant_id | text | N |  |
| run_id | text | Y |  |
| topic | text | Y |  |
| niche | text | Y |  |
| viral_score | numeric | Y |  |
| llm_provider | text | Y |  |
| status | text | Y |  |
| youtube_url | text | Y |  |
| youtube_video_id | text | Y |  |
| elapsed_seconds | numeric | Y |  |
| qc_passed | boolean | Y |  |
| error_message | text | Y |  |
| run_metadata | jsonb | Y |  |
| created_at | timestamp with time zone | N | now() |
| channel_id | text | Y |  |

**Constraints:**
- FK `production_runs_queue_id_fkey`: FOREIGN KEY (queue_id) REFERENCES pipeline_queue(id)
- PK `production_runs_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.production_runs USING btree (created_at DESC)
- public.production_runs USING btree (tenant_id)
- public.production_runs USING btree (id)

**RLS policies:**
- `production_runs_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)

## production_schedules  (rows=5, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| schedule_id | uuid | N | gen_random_uuid() |
| channel_id | character varying | N |  |
| tenant_id | text | N |  |
| cron_expression | character varying | N |  |
| niche_id | character varying | Y |  |
| niche_focus | text | Y |  |
| is_active | boolean | Y | true |
| created_at | timestamp without time zone | Y | now() |
| content_type | character varying | Y | 'short'::character varying |

**Constraints:**
- FK `production_schedules_niche_id_fkey`: FOREIGN KEY (niche_id) REFERENCES niches(niche_id)
- PK `production_schedules_pkey`: PRIMARY KEY (schedule_id)

**Indexes:**
- public.production_schedules USING btree (channel_id, is_active)
- public.production_schedules USING btree (tenant_id, is_active)
- public.production_schedules USING btree (schedule_id)

**RLS policies:**
- `production_schedules_tenant_insert` INSERT roles={-} USING(None) WITH CHECK((tenant_id = (auth.uid())::text))
- `production_schedules_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)
- `production_schedules_tenant_update` UPDATE roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK((tenant_id = (auth.uid())::text))

## tenant_configs  (rows=1, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | uuid | N | gen_random_uuid() |
| tenant_id | text | N |  |
| tts_provider | text | Y | 'edge_tts'::text |
| tts_voice | text | Y | 'en-US-GuyNeural'::text |
| tts_api_key | text | Y |  |
| visual_provider | text | Y | 'pexels'::text |
| visual_max_clip_mb | integer | Y | 50 |
| visual_api_key | text | Y |  |
| visual_ai_model | text | Y |  |
| llm_provider | text | Y | 'openai'::text |
| llm_model | text | Y | 'gpt-4o-mini'::text |
| llm_api_key | text | Y |  |
| niche | text | Y | 'universe_mysteries'::text |
| videos_per_day | integer | Y | 1 |
| publish_platforms | _text[] | Y | '{youtube}'::text[] |
| production_cron | text | Y | '0 1 * * *'::text |
| analytics_cron | text | Y | '0 13 * * *'::text |
| created_at | timestamp with time zone | Y | now() |
| updated_at | timestamp with time zone | Y | now() |
| plan_type | text | Y | 'starter'::text |
| max_videos_per_day | integer | Y | 1 |
| publish_slots | _text[] | Y | '{13:00}'::text[] |
| peak_region | text | Y | 'us'::text |
| auto_schedule | boolean | Y | true |
| is_developer | boolean | Y | false |
| discount_pct | integer | Y | 0 |
| visual_mode | text | Y | 'video'::text |
| tts_voice_per_niche | jsonb | Y | '{"fun_facts": "21m00Tcm4TlvDq8ikWAM", "dark_histo |
| script_min_viral_score | integer | Y | 80 |
| script_max_retry | integer | Y | 3 |
| music_enabled | boolean | Y | false |
| caption_style | jsonb | Y | '{"margin_v": 380, "font_size": 68, "max_lines": 2 |
| music_volume | double precision | Y | 0.18 |
| tts_voice_settings | jsonb | Y | '{"fun_facts": {"speed": 0.90, "style": 0.35, "sta |
| niche_mode | text | Y | 'fixed'::text |
| niche_pool | _text[] | Y | ARRAY['universe_mysteries'::text] |
| duplicate_lookback_days | integer | N | 30 |
| tts_fallback_provider | text | N | 'edge_tts'::text |
| visual_fallback_mode | text | N | 'video'::text |
| llm_script_fallback | text | N | 'gpt-4o-mini'::text |
| production_on_api_error | text | N | 'fallback'::text |
| channel_group | text | N | 'default'::text |
| trailing_silence | double precision | N | 2.5 |
| thumbnail_enabled | boolean | N | true |
| thumbnail_source | text | N | 'ai_generate'::text |
| hook_title_style | jsonb | N | '{"shadow": 3, "enabled": true, "outline": 4, "fon |
| niche_hashtags | jsonb | N | '{"fun_facts": ["#FunFacts", "#MindBlown", "#DidYo |
| telegram_chat_id | text | Y |  |
| telegram_notify_enabled | boolean | N | true |
| telegram_enabled | boolean | Y | true |
| channel_name | character varying | Y | ''::character varying |
| loop_ending_enabled | boolean | Y | true |
| loop_ending_duration | double precision | Y | 1.5 |
| default_niche_rotation | jsonb | Y | '[]'::jsonb |
| niche_rotation_index | integer | Y | 0 |
| youtube_api_key | character varying | Y |  |
| viral_score_weights | jsonb | Y | '{}'::jsonb |
| image_quality | character varying | Y | 'low'::character varying |
| is_active | boolean | N | true |
| timezone | text | N | 'UTC'::text |
| llm_library | text | Y |  |
| llm_models | jsonb | Y |  |
| niche_fallback | text | Y |  |
| music_default_mood | text | Y |  |
| display_handle | text | Y |  |
| subscription_status | text | Y | 'active'::text |
| current_period_end | timestamp with time zone | Y |  |
| trial_started_at | timestamp with time zone | Y |  |

**Constraints:**
- CHECK `chk_production_on_api_error`: CHECK ((production_on_api_error = ANY (ARRAY['fallback'::text, 'stop_and_notify'::text])))
- CHECK `chk_thumbnail_source`: CHECK ((thumbnail_source = ANY (ARRAY['ai_generate'::text, 'hook_frame'::text])))
- PK `tenant_configs_pkey`: PRIMARY KEY (id)
- UNIQUE `tenant_configs_tenant_id_key`: UNIQUE (tenant_id)

**Indexes:**
- public.tenant_configs USING btree (tenant_id)
- public.tenant_configs USING btree (id)
- public.tenant_configs USING btree (tenant_id)

**RLS policies:**
- `tenant_configs_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)

## tenant_credentials  (rows=1, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| tenant_id | text | N |  |
| google_client_id | text | Y |  |
| google_client_secret_enc | text | Y |  |
| google_refresh_token_enc | text | Y |  |
| google_access_token_enc | text | Y |  |
| token_expiry | timestamp with time zone | Y |  |
| channel_id | text | Y |  |
| scopes | jsonb | N | '[]'::jsonb |
| created_at | timestamp with time zone | N | now() |
| updated_at | timestamp with time zone | N | now() |

**Constraints:**
- PK `tenant_credentials_pkey`: PRIMARY KEY (tenant_id)

**Indexes:**
- public.tenant_credentials USING btree (tenant_id)

## tts_profiles  (rows=3, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| provider_key | text | N |  |
| tts_class | text | N |  |
| delivery_wps | numeric | N |  |
| has_word_timeframe | boolean | Y | false |
| speed_param | text | Y |  |
| is_active | boolean | Y | true |
| updated_at | timestamp with time zone | Y | now() |

**Constraints:**
- PK `tts_profiles_pkey`: PRIMARY KEY (provider_key)

**Indexes:**
- public.tts_profiles USING btree (provider_key)

**RLS policies:**
- `tts_profiles_read` SELECT roles={-} USING(true) WITH CHECK(None)

## video_analytics  (rows=3182, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | uuid | N | gen_random_uuid() |
| video_id | text | N |  |
| tenant_id | text | N |  |
| platform | text | N |  |
| views | bigint | Y | 0 |
| likes | bigint | Y | 0 |
| comments | bigint | Y | 0 |
| shares | bigint | Y | 0 |
| collected_at | timestamp with time zone | Y | now() |
| niche | character varying | Y |  |
| title | text | Y |  |
| hook_text | text | Y |  |
| watch_time_mins | integer | Y | 0 |
| avg_view_pct | double precision | Y | 0 |
| ctr | double precision | Y | 0 |
| subscriber_gain | integer | Y | 0 |
| has_full_analytics | boolean | Y | false |
| published_at | timestamp without time zone | Y |  |
| channel_id | character varying | Y |  |
| content_type | character varying | Y |  |
| views_per_sub | double precision | Y | 0 |
| analytics_date | date | Y | CURRENT_DATE |
| fetched_at | timestamp without time zone | Y | now() |

**Constraints:**
- PK `video_analytics_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.video_analytics USING btree (tenant_id)
- public.video_analytics USING btree (video_id)
- public.video_analytics USING btree (tenant_id, niche)
- public.video_analytics USING btree (published_at DESC)
- public.video_analytics USING btree (tenant_id)
- public.video_analytics USING btree (id)

**RLS policies:**
- `video_analytics_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)

## videos  (rows=212, RLS=ON)
| col | type | null | default |
|---|---|---|---|
| id | uuid | N | gen_random_uuid() |
| tenant_id | text | N |  |
| run_id | text | N |  |
| platform | text | N |  |
| video_id | text | Y |  |
| url | text | Y |  |
| title | text | Y |  |
| hook | text | Y |  |
| niche | text | Y |  |
| viral_score | double precision | Y |  |
| status | text | Y | 'published'::text |
| published_at | timestamp with time zone | Y | now() |
| created_at | timestamp with time zone | Y | now() |
| topic | text | Y |  |
| topic_slug | text | Y |  |
| channel_id | uuid | Y |  |
| qc_passed | boolean | Y |  |
| qc_reason | text | Y |  |
| duration_secs | double precision | Y |  |
| file_size_mb | double precision | Y |  |
| topic_scores | jsonb | Y | '{}'::jsonb |
| insights_grade | character varying | Y | ''::character varying |
| voice_id | text | Y |  |
| hook_pattern | text | Y |  |
| music_mood | text | Y |  |
| visual_seed | bigint | Y |  |

**Constraints:**
- CHECK `chk_video_status`: CHECK ((status = ANY (ARRAY['published'::text, 'qc_failed'::text, 'failed'::text])))
- FK `videos_channel_id_fkey`: FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE SET NULL
- PK `videos_pkey`: PRIMARY KEY (id)

**Indexes:**
- public.videos USING btree (channel_id)
- public.videos USING btree (tenant_id, niche, published_at DESC)
- public.videos USING btree (platform)
- public.videos USING btree (tenant_id, status, published_at DESC)
- public.videos USING btree (tenant_id)
- public.videos USING btree (tenant_id, topic_slug, niche, published_at)
- public.videos USING btree (id)

**RLS policies:**
- `videos_tenant_read` SELECT roles={-} USING((tenant_id = (auth.uid())::text)) WITH CHECK(None)

## Functions (public)
- `dispatch_pipeline_jobs()` → void
- `handle_new_tenant()` → trigger [SECURITY DEFINER]
- `rls_auto_enable()` → event_trigger [SECURITY DEFINER]
- `set_tenant_config(p_llm_api_key text, p_visual_api_key text, p_tts_api_key text, p_youtube_api_key text, p_llm_library text, p_tts_provider text, p_tts_voice text, p_timezone text, p_display_handle text, p_telegram_chat_id text, p_telegram_enabled boolean)` → void [SECURITY DEFINER]

## Triggers (public)

**auth.* triggers:**
- CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION handle_new_tenant()
