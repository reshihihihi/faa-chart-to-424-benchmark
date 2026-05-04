# 瀹為獙缁? SFT 鎷撳睍瀹為獙褰撳墠鏂规锛坰moke5锛?
鏃ユ湡锛?026-05-03
褰撳墠鍒嗘敮锛歚group1-sft-extension-plan-20260503`
褰撳墠 commit锛歚57d5c86`
褰撳墠闃舵锛氬厛鍋?5 鏉℃牱鏈?smoke锛屼笉璺戝叏閲忋€?
## 1. 杩欐瀹為獙鍒板簳瑕佸仛浠€涔?
瀹為獙缁?鍘熸潵宸茬粡鏈変竴濂?formal300 / formal200 璇勬祴娴佺▼銆傜幇鍦ㄦ柊澧炵殑鏄?SFT 鎷撳睍瀹為獙锛屼篃灏辨槸鎶?Qwen2-VL 鐩稿叧鐨?SFT/LoRA 鏂规硶绾冲叆瀹為獙缁?鐨勮瘎娴嬫鏋朵腑銆?
鏈疆涓嶆槸鐩存帴璺戝叏閲忥紝涔熶笉鏄┈涓婅缁冩柊鐨勬ā鍨嬨€傛湰杞洰鏍囨槸鍏堥獙璇侊細

1. 浠撳簱閲岀殑 SFT run-package 鑴氭湰鏄惁鍒颁綅銆?2. 鏈満璺緞銆佹ā鍨嬨€佸浘鐗囥€乼arget銆乻coring manifest 鏄惁鑳芥帴閫氥€?3. 5 鏉℃牱鏈殑 smoke package 鏄惁鑳界敓鎴愩€?4. 鍏堣窇涓や釜鏈€鍏抽敭鐨勬柟娉曪細
   - `D_BASE_SAME_BACKBONE`锛氬悓搴曞骇鏈井璋冨鐓с€?   - `D1`锛氬凡鏈?D1 LoRA/checkpoint 鐨勫璺戙€?
鍙湁杩欎袱涓?5 鏍锋湰 smoke 璺戦€氬苟鑳借瘎鍒嗗悗锛屾墠鑰冭檻鍚庣画鎵╁睍鏂规硶鎴栧叏閲忋€?
## 2. 褰撳墠宸茬粡瀹屾垚鐨勪簨鎯?
宸茬粡鎵ц骞剁‘璁わ細

1. `git pull` 宸叉媺鍒版渶鏂拌ˉ涓併€?2. HEAD 鏄?`57d5c86`銆?3. 浠ヤ笅 4 涓叧閿枃浠跺凡缁忓瓨鍦細
   - `scripts/group1_sft/prepare_group1_sft_run_package.py`
   - `scripts/group1_sft/run_qwen2vl_group1_sft_inference.py`
   - `training/group1_sft/manifests/evidence_record.schema.json`
   - `training/group1_sft/manifests/evidence_questionnaire.schema.json`

宸茬粡鍒涘缓骞跺～鍐欙細

```text
training/group1_sft/configs/local_paths.local.json
```

杩欎釜鏂囦欢鏄湰鏈鸿矾寰勯厤缃紝涓嶅簲鎻愪氦鍒?Git銆?
宸茬粡閫氳繃璺緞妫€鏌ワ細

```powershell
python scripts\group1_sft\validate_group1_sft_workspace.py --paths training\group1_sft\configs\local_paths.local.json
```

缁撴灉锛歳equired 璺緞鍏ㄩ儴瀛樺湪锛宍ready: true`銆?
宸茬粡鐢熸垚杩囦竴娆?5 鏍锋湰 smoke package锛?
```text
<group1_sft-artifact-root>\runs\group1_sft_smoke5
```

璇?package 宸茬粡纭浣跨敤锛?
- `scoring_equivalence_v2`
- `canonical_proxy_gt_chart_display_v2.json`
- `comparison_policy_v2.jsonl`
- `field_targets_chart_display_v2.jsonl`

杩欑鍚堟湰杞姹傦細run package 蹇呴』浼樺厛浣跨敤 scoring equivalence v2 target 鍜?comparison policy v2銆?
## 3. 褰撳墠鍑虹幇鐨勯棶棰?
褰撳墠闂涓嶆槸 `D_BASE_SAME_BACKBONE` 鎴?`D1` 澶辫触銆?
闂鏄細`prepare_group1_sft_run_package.py` 榛樿浼氭妸 5 涓柟娉曢兘鏀捐繘 package锛?
```text
D_BASE_SAME_BACKBONE
D1
EVIDENCE_TO_SEMANTICS_SFT
CHART_TO_EVIDENCE_SFT
TWO_STAGE_AUTO_SFT
```

浣嗘湰杞敤鎴疯姹傚厛鍙窇涓や釜鏂规硶锛?
```text
D_BASE_SAME_BACKBONE
D1
```

鎵€浠ョ涓€娆＄敓鎴愮殑 package 閲屽嚭鐜颁簡 2 涓?blocker锛?
1. `EVIDENCE_TO_SEMANTICS_SFT` 缂哄皯鏈湴 evidence eval JSONL锛?
```text
<group1_sft-artifact-root>\eval_jsonl\evidence_to_semantics_formal200.jsonl
```

2. `TWO_STAGE_AUTO_SFT` 闇€瑕佸厛鏈?`CHART_TO_EVIDENCE_SFT` 鐨勮緭鍑猴紝涓嶈兘鐩存帴浣滀负绗竴姝ヨ繍琛屻€?
杩欎袱涓?blocker 灞炰簬鈥滈澶栨柟娉曟殏鏃舵湭鍑嗗濂解€濓紝涓嶆槸鏈疆 smoke 鐨勬牳蹇冮樆濉炪€?
瀵规湰杞璺戠殑 `D_BASE_SAME_BACKBONE` 鍜?`D1`锛屽綋鍓嶆鏌ョ粨鏋滄槸锛?
- input rows锛?
- missing images锛?
- image sha256 mismatch锛?
- base model path锛氬瓨鍦?- D1 LoRA/checkpoint path锛氬瓨鍦?
## 4. 閲嶈杈圭晫瑕佹眰

鏁翠釜瀹為獙蹇呴』閬靛畧浠ヤ笅杈圭晫锛?
1. 涓嶆彁浜よ繖浜涙湰鏈烘枃浠舵垨澶ф枃浠讹細
   - `local_paths.local.json`
   - 妯″瀷鐩綍
   - checkpoint / LoRA
   - PNG 鍥剧墖
   - raw outputs
   - 澶х粨鏋滅洰褰?
2. 鎺ㄧ悊闃舵绂佹璇诲彇锛?   - target JSON
   - score 鏂囦欢
   - raw 424 / CIFP
   - 鍏朵粬鏂规硶棰勬祴

3. `scoring_manifest` 鍙兘鐢ㄤ簬棰勬祴瀹屾垚鍚庣殑璇勫垎銆?
4. 鏈疆鍙窇 5 鏉℃牱鏈?smoke锛屼笉璺?full formal200 / formal300銆?
5. 褰撳墠鍙窇锛?   - `D_BASE_SAME_BACKBONE`
   - `D1`

## 5. 涓嬩竴姝ュ簲璇ュ仛浠€涔?
涓嬩竴姝ュ簲璇ラ噸鏂扮敓鎴愪竴涓彧鍖呭惈 `D_BASE_SAME_BACKBONE` 鍜?`D1` 鐨?smoke5 package銆?
鍘熷洜锛氱涓€娆?package 榛樿鍖呭惈浜嗛澶栨柟娉曪紝鎵€浠ヤ骇鐢熶簡涓庢湰杞棤鍏崇殑 blocker銆?
閲嶆柊闄愬畾鏂规硶鍚庯紝preflight blocker 搴旇娓呴浂銆?
鍦ㄤ粨搴撴牴鐩綍杩愯锛?
```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py `
  --paths training\group1_sft\configs\local_paths.local.json `
  --limit 5 `
  --run-id group1_sft_smoke5 `
  --methods D_BASE_SAME_BACKBONE,D1 `
  --overwrite
```

鐒跺悗鎵撳紑妫€鏌ワ細

```text
<group1_sft-artifact-root>\runs\group1_sft_smoke5\reports\preflight_report_zh.md
<group1_sft-artifact-root>\runs\group1_sft_smoke5\RUN_COMMANDS.md
```

濡傛灉 `preflight_report_zh.md` 涓?blockers 涓?`0`锛屽啀杩涘叆鎺ㄧ悊銆?
## 6. smoke 鎺ㄧ悊椤哄簭

蹇呴』鍏堣窇鏈井璋冨悓搴曞骇瀵圭収锛?
```text
D_BASE_SAME_BACKBONE
```

鍙湁瀹冩垚鍔熷悗锛屽啀璺戯細

```text
D1
```

鍏蜂綋鍛戒护浠ョ敓鎴愮洰褰曢噷鐨?`RUN_COMMANDS.md` 涓哄噯锛屼笉鎵嬪啓鏇挎崲瀹為獙瀹氫箟銆?
褰撳墠棰勮鍛戒护褰㈡€佸涓嬨€?
### 6.1 D_BASE_SAME_BACKBONE

```powershell
python scripts\group1_sft\run_qwen2vl_group1_sft_inference.py `
  --method D_BASE_SAME_BACKBONE `
  --input-manifest <group1_sft-artifact-root>\runs\group1_sft_smoke5\D_BASE_SAME_BACKBONE\input_manifest.jsonl `
  --model-dir <local-hf-cache>\models--Qwen--Qwen2-VL-2B-Instruct\snapshots\895c3a49bc3fa70a340399125c650a463535e71c `
  --prompt training\d_sft\prompts\d_sft_image_to_canonical.v2.md `
  --json-schema schemas\missed_approach_leg.schema.json `
  --scoring-manifest <group1_sft-artifact-root>\runs\group1_sft_smoke5\scoring_manifest.jsonl `
  --output-root <group1_sft-artifact-root>\runs\group1_sft_smoke5\D_BASE_SAME_BACKBONE
```

### 6.2 D1

```powershell
python scripts\group1_sft\run_qwen2vl_group1_sft_inference.py `
  --method D1 `
  --input-manifest <group1_sft-artifact-root>\runs\group1_sft_smoke5\D1\input_manifest.jsonl `
  --model-dir <local-hf-cache>\models--Qwen--Qwen2-VL-2B-Instruct\snapshots\895c3a49bc3fa70a340399125c650a463535e71c `
  --adapter-checkpoint <d_sft-artifact-root>\checkpoints\d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1\checkpoint-final `
  --prompt training\d_sft\prompts\d_sft_image_to_canonical.v2.md `
  --json-schema schemas\missed_approach_leg.schema.json `
  --scoring-manifest <group1_sft-artifact-root>\runs\group1_sft_smoke5\scoring_manifest.jsonl `
  --output-root <group1_sft-artifact-root>\runs\group1_sft_smoke5\D1
```

## 7. 鎺ㄧ悊瀹屾垚鍚庤姹囨姤浠€涔?
涓や釜鏂规硶閮借窇瀹屽悗锛岄渶瑕佸垎鍒鍙栵細

```text
<group1_sft-artifact-root>\runs\group1_sft_smoke5\D_BASE_SAME_BACKBONE\summary_report.json
<group1_sft-artifact-root>\runs\group1_sft_smoke5\D1\summary_report.json
```

鏈€缁堟眹鎶ュ簲鍖呭惈锛?
1. git commit hash锛歚57d5c86`
2. `local_paths.local.json` 鍏抽敭璺緞鏄惁瀛樺湪
3. preflight blocker 鏁伴噺
4. `D_BASE_SAME_BACKBONE` 鐨?`summary_report.json` 璺緞鍜?score
5. `D1` 鐨?`summary_report.json` 璺緞鍜?score
6. parse failure 鏁伴噺
7. schema failure 鏁伴噺
8. 鏄惁鏈変换浣曚唬鐮佹敼鍔?
## 8. 鍚庣画鎵╁睍鏂规硶浠€涔堟椂鍊欏仛

`EVIDENCE_TO_SEMANTICS_SFT`銆乣CHART_TO_EVIDENCE_SFT`銆乣TWO_STAGE_AUTO_SFT` 鏄悗缁?SFT 鎷撳睍鏂瑰悜锛屼絾涓嶆槸鏈疆绗竴姝ャ€?
寤鸿椤哄簭鏄細

1. 鍏堝畬鎴?`D_BASE_SAME_BACKBONE` 鍜?`D1` 鐨?smoke5銆?2. 纭鎺ㄧ悊銆佽В鏋愩€乻chema 鏍￠獙銆乻coring 閮借兘閫氥€?3. 鍐嶈ˉ榻愭垨瀹氫綅 evidence / chart-to-evidence 鎵€闇€鐨?eval JSONL 鍜?checkpoint銆?4. 鍐嶅崟鐙敓鎴愬寘鍚柊 SFT 鏂规硶鐨?smoke package銆?5. 鏂版柟娉?smoke 鎴愬姛鍚庯紝鎵嶈繘鍏ユ洿澶ф牱鏈垨鍏ㄩ噺銆?
杩欐牱鍋氱殑鍘熷洜鏄細鍏堣瘉鏄庡綋鍓?D 绯诲垪鎺ㄧ悊涓庤瘎鍒嗛摼璺病闂锛屽啀鎶婃柊 SFT 涓棿浠诲姟鎺ヨ繘鏉ワ紝鍙互鏇村鏄撳畾浣嶉敊璇潵婧愩€?
