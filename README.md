# MSUT鍏ㄦ爤璁よ瘉绯荤粺

> 閲嶈鍙樻洿锛氭湰椤圭洰鍚庣宸蹭粠 Node.js + Express 閲嶆瀯涓?Python + FastAPI锛孉PI 涓庤涓轰繚鎸佸吋瀹癸紝鍓嶇鏃犻渶鏀瑰姩鍗冲彲宸ヤ綔銆傝鎯呰鏂囨湯鈥滈噸瑕佸彉鏇达細鍚庣宸查噸鏋勪负 Python/FastAPI鈥濄€?

鍩轰簬 Python + FastAPI + Vue.js + TypeScript 鏋勫缓鐨勭幇浠ｅ寲鍏ㄦ爤璁よ瘉涓庤祫婧愮鐞嗙郴缁燂紒

## 馃Л 閲嶈鍙樻洿锛氬悗绔凡閲嶆瀯涓?Python/FastAPI

鏈」鐩殑鍚庣宸蹭粠 Node.js + Express 瀹屾暣杩佺Щ涓?Python + FastAPI锛孉PI 璺緞銆佽姹傚拰鍝嶅簲缁撴瀯淇濇寔涓嶅彉锛屽墠绔棤闇€鏀瑰姩鍗冲彲宸ヤ綔銆?

- 鏍稿績瑕佺偣

  - 鏇挎崲鍘?`server/src/*.ts` 瀹炵幇锛屾柊澧?Python 浠ｇ爜浜?`server/` 鐩綍銆?
  - 琛屼负涓€鑷达細閴存潈銆丆ookie锛圫ameSite/secure锛夈€佸垎椤点€侀敊璇繑鍥炪€佷笅杞藉搷搴斿ご鍧囦笌鍘熷疄鐜板榻愩€?
  - 闈欐€佷笂浼犵洰褰曚粛涓?`/uploads`锛屽叕寮€璁块棶銆侀暱缂撳瓨銆?
  - SQLite 缁撴瀯淇濇寔涓嶅彉锛屼繚鐣欎粠 `email` 鈫?`username` 鐨勮嚜鍔ㄨ縼绉汇€?
- 鏂板悗绔妧鏈爤

  - Python 3.11+銆丗astAPI銆乁vicorn
  - SQLite锛坄sqlite3`锛夈€丳yJWT銆乥crypt銆乸ython-multipart
- 鍏抽敭鏂囦欢锛堝悗绔級

  - `server/app.py`锛氬簲鐢ㄥ叆鍙ｏ紙鎸傝浇璺敱涓庨潤鎬佺洰褰曘€佸惎鍔ㄨ縼绉汇€佸熀纭€瀹夊叏澶达級
  - `server/auth.py`锛氳璇佹帴鍙ｏ紙register/login/logout/me锛?
  - `server/files.py`锛氳祫婧愪笌鏂囦欢鎺ュ彛锛堝垱寤?涓婁紶/鍒楄〃/璇︽儏/鏇存柊/鍒犻櫎/涓嬭浇锛?
  - `server/db.py`锛氭暟鎹簱杩炴帴銆佸垵濮嬪寲涓庤縼绉?
  - `server/utils.py`锛氬伐鍏峰嚱鏁帮紙nanoid銆乻lug銆丆ookie 閫夐」銆佸竷灏旇В鏋愶級
  - `server/schemas.py`锛氱被鍨嬪０鏄庯紙JWT 杞借嵎锛?
  - `server/requirements.txt`锛氬悗绔緷璧栨竻鍗?
  - 鏁版嵁/鏂囦欢榛樿浣嶇疆锛歚server/data.sqlite`銆乣server/uploads/`
- 鏈湴寮€鍙?

  - 瀹夎渚濊禆锛歚python -m pip install -r server/requirements.txt`
  - 鍚姩鍚庣锛堝紑鍙戯級锛歚npm run dev:server`锛堢瓑浠?`python -m uvicorn server.app:app --reload --port 3000`锛?
  - 鍚姩鍓嶇锛堝紑鍙戯級锛歚npm run dev:client`锛圴ite 浠ｇ悊 `/api` 鈫?`http://localhost:3000`锛?
- Docker 涓庨儴缃?

  - `Dockerfile` 宸叉洿鏂颁负 Python 鍚庣 + Nginx 鍓嶇锛汣ompose 鍋ュ悍妫€鏌ユ寚鍚?`http://localhost:3400/api/auth/me`銆?
  - 鍏稿瀷鍛戒护锛歚docker build -t msut-auth-system:py .`锛宍docker-compose up -d`
  - 鍗蜂笌璺緞锛歚/app/server/uploads`銆乣/app/server/data.sqlite`
- 鐜鍙橀噺锛堜笌鍘熷疄鐜颁繚鎸佷竴鑷达級

  - `PORT`锛氬悗绔鍙ｏ紙寮€鍙?3000锛孌ocker 榛樿 3400锛?
  - `JWT_SECRET`锛欽WT 瀵嗛挜锛堢敓浜у繀閰嶏級
  - `NODE_ENV`锛氳繍琛岀幆澧冿紙`production` 鏃堕粯璁ゅ惎鐢?HTTPS 鐩稿叧琛屼负锛?
  - `PUBLIC_BASE_URL`锛氱敤浜庣敓鎴愯祫婧愬垎浜摼鎺?
  - `HTTPS_ENABLED`锛氭槸鍚﹀惎鐢?HTTPS锛堝喅瀹?Cookie SameSite/secure 涓?HSTS锛?
  - `COOKIE_DOMAIN`锛欳ookie 鍩熷悕锛堝彲閫夛級
- API 鍏煎鎬?

  - 璺緞涓庢柟娉曚繚鎸佷笉鍙橈細
    - `POST /api/auth/register`銆乣POST /api/auth/login`銆乣POST /api/auth/logout`銆乣GET /api/auth/me`
    - `GET /api/private/ping`锛堥渶鐧诲綍锛?
    - `POST /api/resources`锛堥渶鐧诲綍锛夈€乣GET /api/resources`銆乣GET /api/resources/:slug`
    - `PATCH /api/resources/:id`锛堥渶鐧诲綍锛夈€乣DELETE /api/resources/:id`锛堥渶鐧诲綍锛?
    - `POST /api/files/upload`锛堥渶鐧诲綍锛屽瓧娈靛悕 `files`锛屾渶澶?10 涓紝鍗曟枃浠?50MB锛?
    - `GET /api/files/:id/download`
  - 閿欒杩斿洖 `{ error: string }`锛涗笅杞戒娇鐢?`Content-Disposition: attachment; filename*=` UTF-8 鐧惧垎鍙风紪鐮併€?
- 澶囨敞

  - 鏃х殑 TypeScript 鏈嶅姟鍣ㄤ唬鐮佷粛鍦ㄤ粨搴撲腑锛屼絾宸蹭笉鍐嶈浣跨敤锛堝紑鍙戣剼鏈笌 Docker 鍧囦娇鐢?Python 鐗堟湰锛夈€?

## 馃殌 鎶€鏈爤

### 鍚庣

- **Node.js** 20.18.0 + **Express** 妗嗘灦
- **TypeScript** 鎻愪緵绫诲瀷瀹夊叏
- **SQLite** 鏁版嵁搴?(better-sqlite3)
- **JWT** 韬唤璁よ瘉
- **bcryptjs** 瀵嗙爜鍔犲瘑
- **multer** 鏂囦欢涓婁紶澶勭悊

### 鍓嶇

- **Vue.js** 3.5.21 + **TypeScript**
- **Vite** 鏋勫缓宸ュ叿
- **Element Plus** UI 缁勪欢搴?
- **Pinia** 鐘舵€佺鐞?
- **Vue Router** 璺敱绠＄悊

### 閮ㄧ讲

- **Docker** 瀹瑰櫒鍖栭儴缃?
- **Nginx** 鍙嶅悜浠ｇ悊鍜岄潤鎬佹枃浠舵湇鍔?
- 鏀寔鍥藉唴闀滃儚婧愬姞閫?

## 馃摝 鍔熻兘鐗规€?

- 鉁?鐢ㄦ埛娉ㄥ唽/鐧诲綍/娉ㄩ攢
- 鉁?JWT 韬唤璁よ瘉
- 鉁?璧勬簮绠＄悊绯荤粺
- 鉁?鏂囦欢涓婁紶鍔熻兘
- 鉁?鍝嶅簲寮忚璁?
- 鉁?Docker 瀹瑰櫒鍖栭儴缃?
- 鉁?鐢熶骇鐜浼樺寲

## 馃洜锔?蹇€熷紑濮?

### 鐜瑕佹眰

- Node.js 20.18.0+
- Docker (鍙€?

### 鏈湴寮€鍙?

```bash
# 瀹夎渚濊禆
npm install

# 鍚姩鍚庣寮€鍙戞湇鍔″櫒
npm run dev:server

# 鍚姩鍓嶇寮€鍙戞湇鍔″櫒
npm run dev:client

# 鍚屾椂鍚姩鍓嶅悗绔?
npm run dev:all
```

璁块棶鍦板潃锛?

- 鍓嶇: http://localhost:5173
- 鍚庣 API: http://localhost:3400

### Docker 閮ㄧ讲

#### 鏍囧噯鏋勫缓

```bash
# 鏋勫缓闀滃儚
docker build -t msut-auth-system:1.0.0 .

# 杩愯瀹瑰櫒
docker run -d \
  --name msut-auth-app \
  -p 1122:80 \
  -p 3400:3400 \
  -e JWT_SECRET=your-super-secret-jwt-key \
  -e NODE_ENV=production \
  -v msut-uploads:/app/server/uploads \
  --restart unless-stopped \
  msut-auth-system:1.0.0
```

#### 鍥藉唴闀滃儚婧愭瀯寤猴紙鎺ㄨ崘鍥藉唴鐢ㄦ埛锛?

```bash
# 浣跨敤鍥藉唴闀滃儚婧愭瀯寤?
docker build -f Dockerfile.cn -t msut-auth-system:1.0.0-cn .

# 鎴栦娇鐢?Docker Compose
docker-compose up -d
```

#### 楠岃瘉閮ㄧ讲

```bash
# 妫€鏌ュ鍣ㄧ姸鎬?
docker ps

# 娴嬭瘯鍓嶇璁块棶
curl http://localhost:1122

# 娴嬭瘯鍚庣API
curl http://localhost:3400/api/auth/me

# 鏌ョ湅鏃ュ織
docker logs msut-auth-app
```

## 馃搧 椤圭洰缁撴瀯

```
msut涓荤珯/
鈹溾攢鈹€ server/                 # 鍚庣浠ｇ爜
鈹?  鈹溾攢鈹€ src/
鈹?  鈹?  鈹溾攢鈹€ auth.ts        # 璁よ瘉閫昏緫
鈹?  鈹?  鈹溾攢鈹€ db.ts          # 鏁版嵁搴撹繛鎺?
鈹?  鈹?  鈹溾攢鈹€ files.ts       # 鏂囦欢绠＄悊
鈹?  鈹?  鈹斺攢鈹€ index.ts       # 鍏ュ彛鏂囦欢
鈹?  鈹溾攢鈹€ uploads/           # 涓婁紶鏂囦欢鐩綍
鈹?  鈹斺攢鈹€ package.json
鈹溾攢鈹€ melon-tech-web/        # 鍓嶇浠ｇ爜
鈹?  鈹溾攢鈹€ src/
鈹?  鈹?  鈹溾攢鈹€ api/           # API 鎺ュ彛
鈹?  鈹?  鈹溾攢鈹€ components/    # 鍏叡缁勪欢
鈹?  鈹?  鈹溾攢鈹€ router/        # 璺敱閰嶇疆
鈹?  鈹?  鈹溾攢鈹€ stores/        # 鐘舵€佺鐞?
鈹?  鈹?  鈹斺攢鈹€ views/         # 椤甸潰缁勪欢
鈹?  鈹斺攢鈹€ package.json
鈹溾攢鈹€ Dockerfile             # Docker 鏋勫缓鏂囦欢
鈹溾攢鈹€ Dockerfile.cn          # 鍥藉唴闀滃儚婧愮増鏈?
鈹溾攢鈹€ docker-compose.yml     # Docker Compose 閰嶇疆
鈹斺攢鈹€ README.md
```

## 馃敡 鐜鍙橀噺

### 鍚庣鐜鍙橀噺

- `PORT`: 鏈嶅姟鍣ㄧ鍙?(榛樿: 3400)
- `JWT_SECRET`: JWT 瀵嗛挜 (鐢熶骇鐜蹇呴』淇敼)
- `NODE_ENV`: 杩愯鐜 (development/production)
- `PUBLIC_BASE_URL`: 鍏叡璁块棶鍦板潃
- `HTTPS_ENABLED`: 鏄惁鍚敤HTTPS (榛樿: false)
- `COOKIE_DOMAIN`: Cookie鍩熷悕璁剧疆 (鍙€?

### 鍓嶇鐜鍙橀噺

- `VITE_PUBLIC_BASE_URL`: API 鍩虹鍦板潃

## 馃攼 瀹夊叏鐗规€?

- 鉁?瀵嗙爜bcrypt鍔犲瘑瀛樺偍
- 鉁?JWT token韬唤楠岃瘉
- 鉁?Helmet瀹夊叏涓棿浠?
- 鉁?闈瀝oot鐢ㄦ埛杩愯瀹瑰櫒
- 鉁?鍙鏂囦欢绯荤粺鏉冮檺鎺у埗

## 馃殌 鐢熶骇鐜閮ㄧ讲

1. **淇敼JWT瀵嗛挜**

   ```bash
   export JWT_SECRET=your-very-secure-random-secret-key
   ```
2. **浣跨敤Docker Compose閮ㄧ讲**

   ```bash
   docker-compose up -d
   ```
3. **閰嶇疆鍙嶅悜浠ｇ悊**锛堝彲閫夛級

   - 浣跨敤 Nginx/Apache 浣滀负鍓嶇浠ｇ悊
   - 閰嶇疆 HTTPS 璇佷功
   - 璁剧疆鍩熷悕瑙ｆ瀽

## 馃З DSL 鐢熸垚鍣紙DSL 鈫?.melsave锛?

鏈」鐩凡闆嗘垚鈥滅敎鐡滄父涔愬満鈥滵SL 鍒?.melsave 鐨勫湪绾跨敓鎴愬伐鍏凤細

- 鍓嶇鍏ュ彛锛氬鑸爮涓殑鈥淒SL 宸ュ叿鈥濓紝鏃犻渶鐧诲綍鍗冲彲浣跨敤銆?
- 鍚庣鎺ュ彛锛歚POST /api/melsave/generate`
  - 璇锋眰浣擄細`{ "dsl": "..." }`锛屽唴瀹逛负 input.py 鐨?DSL 鏂囨湰銆?
  - 鍝嶅簲锛歚.melsave` 鏂囦欢瀛楄妭娴侊紱`Content-Disposition` 鍖呭惈 UTF-8 鐧惧垎鍙风紪鐮佺殑鏂囦欢鍚嶃€?
- 寮€鍙戣皟璇曠ず渚嬶細
  ```bash
  curl -X POST http://localhost:3000/api/melsave/generate \
    -H "Content-Type: application/json" \
    -d @dsl.json \
    -o out.melsave
  ```

瀹炵幇璇存槑锛氬悗绔湪姣忔璇锋眰鏃朵細灏嗙敓鎴愬櫒鐩綍澶嶅埗鍒颁复鏃跺伐浣滅洰褰曪紝鍐欏叆 DSL 涓?`input.py` 骞惰繍琛屾祦姘寸嚎锛屽畬鎴愬悗璇诲彇鐢熸垚鐨?`.melsave` 杩斿洖骞舵竻鐞嗕复鏃剁洰褰曪紝閬垮厤骞跺彂鍐欏叆鍐茬獊銆?

## 馃搵 API 鎺ュ彛

### 璁よ瘉鎺ュ彛

- `POST /api/auth/register` - 鐢ㄦ埛娉ㄥ唽
- `POST /api/auth/login` - 鐢ㄦ埛鐧诲綍
- `POST /api/auth/logout` - 鐢ㄦ埛娉ㄩ攢
- `GET /api/auth/me` - 鑾峰彇褰撳墠鐢ㄦ埛淇℃伅

### 璧勬簮鎺ュ彛

- `GET /api/resources` - 鑾峰彇璧勬簮鍒楄〃
- `POST /api/resources` - 鍒涘缓璧勬簮锛堥渶瑕佽璇侊級
- `GET /api/resources/:slug` - 鑾峰彇璧勬簮璇︽儏
- `POST /api/files/upload` - 涓婁紶鏂囦欢锛堥渶瑕佽璇侊級
- `GET /api/files/:id/download` - 涓嬭浇鏂囦欢

### 鏂囦欢鐐硅禐锛堟柊澧烇級

- 浠呯櫥褰曠敤鎴峰彲鐐硅禐锛岃瀹粎鍙煡鐪嬬偣璧炴暟銆?- 鎺ュ彛锛?  - `GET /api/files/likes?ids=1,2,3` 杩斿洖 `{ items: [{ id, likes, liked }] }`
  - `POST /api/files/:id/like` 鐐硅禐锛堝箓绛夛級杩斿洖 `{ liked: true, likes }`
  - `DELETE /api/files/:id/like` 鍙栨秷鐐硅禐杩斿洖 `{ liked: false, likes }`
  - 鍓嶇璧勬簮璇︽儏椤电殑鏂囦欢鍗＄墖鏄剧ず鐐硅禐鏁伴噺骞舵彁渚涚偣璧炴寜閽€?
## 馃摑 寮€鍙戣鏄?

### 鏁版嵁搴?

椤圭洰浣跨敤 SQLite 鏁版嵁搴擄紝鏁版嵁鏂囦欢浣嶄簬 `server/data.sqlite`銆傞娆¤繍琛屼細鑷姩鍒涘缓鎵€闇€鐨勮〃缁撴瀯銆?

### 鏂囦欢涓婁紶

涓婁紶鐨勬枃浠跺瓨鍌ㄥ湪 `server/uploads/` 鐩綍锛屽缓璁湪鐢熶骇鐜涓寕杞藉閮ㄥ瓨鍌ㄥ嵎銆?

### 鏋勫缓浼樺寲

- 澶氶樁娈礑ocker鏋勫缓锛屾渶灏忓寲闀滃儚浣撶Н
- 鍓嶇璧勬簮鍘嬬缉鍜岀紦瀛樹紭鍖?
- 鍚庣渚濊禆鐢熶骇鐜绮剧畝

## 馃 璐＄尞鎸囧崡

1. Fork 椤圭洰
2. 鍒涘缓鐗规€у垎鏀?(`git checkout -b feature/amazing-feature`)
3. 鎻愪氦鏇存敼 (`git commit -m 'Add some amazing feature'`)
4. 鎺ㄩ€佸埌鍒嗘敮 (`git push origin feature/amazing-feature`)
5. 鍒涘缓 Pull Request

## 馃悰 甯歌闂

### Q: 瀹瑰櫒鍚姩澶辫触鎬庝箞鍔烇紵

A: 妫€鏌ョ鍙?122鍜?400鏄惁琚崰鐢紝鏌ョ湅瀹瑰櫒鏃ュ織锛歚docker logs msut-auth-app`

### Q: 鍓嶇椤甸潰绌虹櫧鎬庝箞鍔烇紵

A: 纭鏋勫缓鏄惁鎴愬姛锛屾鏌ユ祻瑙堝櫒鎺у埗鍙伴敊璇俊鎭?

### Q: 鏂囦欢涓婁紶澶辫触鎬庝箞鍔烇紵

A: 妫€鏌ヤ笂浼犵洰褰曟潈闄愬拰纾佺洏绌洪棿锛岀‘璁ocker鍗锋寕杞芥纭?

### Q: 鐧诲綍鐘舵€佹棤娉曠淮鎸佹€庝箞鍔烇紵

A: 妫€鏌TTPS_ENABLED鐜鍙橀噺璁剧疆锛屽鏋滀娇鐢℉TTP璁剧疆涓篺alse锛孒TTPS璁剧疆涓簍rue銆傚悓鏃剁‘璁OOKIE_DOMAIN閰嶇疆鏄惁姝ｇ‘銆?

## 馃搫 璁稿彲璇?

MIT License - 璇﹁ [LICENSE](LICENSE) 鏂囦欢

## 馃啒 鏀寔

濡傛湁闂锛岃鍦?GitHub Issues 涓彁浜ら棶棰樻弿杩般€?

