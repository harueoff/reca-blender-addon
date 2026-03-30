# RECA - All-in-One 3D Toolkit for Blender 5.1.0

A professional-grade, multi-purpose Blender addon with 8 integrated modules.

## Features

| Module | Description |
|--------|-------------|
| **Scene Builder** | 8 lighting presets, 6 camera presets, 5 environment types, quick scene setup |
| **Batch Processor** | 7 batch operations, file scanning, format conversion (OBJ/FBX/GLB/STL/USD) |
| **Procedural Generator** | 8 generators: Building, Terrain, Tree, Rocks, City, Array, Scatter, Pipe |
| **Quick Tools** | Align, Distribute, Mirror, Random Transform, Smart Select, Copy Attributes |
| **Render Manager** | 9 render presets, turntable animation, render all cameras, clay override |
| **Material Tools** | 20 PBR presets, custom material builder, random materials, bake to vertex |
| **MCP Server** | 16 AI-controllable tools via JSON-RPC 2.0, HTTP server for AI agents |
| **AI Integration** | 6 AI providers: OpenClaw, Google Antigravity, Anthropic, OpenAI, Ollama, Custom |

## Installation

1. Download the latest release ZIP
2. In Blender: `Edit > Preferences > Add-ons > Install from Disk`
3. Select the ZIP file and enable "RECA - All-in-One 3D Toolkit"

---

# Huong dan su dung chi tiet (Tieng Viet)

## Cai dat

1. Tai file `reca_v2.0.0.zip` tu trang [Releases](https://github.com/harueoff/reca-blender-addon/releases)
2. Mo Blender 5.1.0
3. Vao `Edit > Preferences > Add-ons`
4. Nhan nut **Install from Disk** (goc tren ben phai)
5. Chon file ZIP vua tai ve
6. Tick vao o **RECA - All-in-One 3D Toolkit** de kich hoat
7. Panel RECA se xuat hien o **Sidebar ben phai** (nhan phim `N` de mo) > Tab **RECA**

---

## Module 1: Scene Builder (Xay dung Scene)

Tao nhanh cac scene chuyen nghiep voi anh sang, camera va moi truong co san.

### Cac chuc nang:

**Thiet lap anh sang (Lighting Presets):**
| Preset | Mo ta |
|--------|-------|
| STUDIO_3POINT | Anh sang studio 3 diem (Key, Fill, Rim) - dung cho san pham |
| STUDIO_SOFT | Anh sang mem - dung cho chan dung |
| OUTDOOR_SUN | Anh sang ngoai troi co nang mat troi |
| INDOOR_WARM | Anh sang noi that am ap |
| DRAMATIC | Anh sang tuong phan manh - tao hieu ung kich tinh |
| NEON | Anh sang neon mau sac |
| GOLDEN_HOUR | Anh sang hoang hon vang |
| MOONLIGHT | Anh sang trang xanh |

**Thiet lap Camera (Camera Presets):**
| Preset | Mo ta |
|--------|-------|
| FRONT | Camera chinh dien |
| THREE_QUARTER | Camera goc 3/4 (goc chup pho bien nhat) |
| TOP_DOWN | Camera nhin tu tren xuong |
| LOW_ANGLE | Camera goc thap nhin len |
| CLOSE_UP | Camera can canh |
| WIDE | Camera goc rong |

**Moi truong (Environment):**
| Loai | Mo ta |
|------|-------|
| INFINITE | Nen vo cuc (backdrop cong) - dung cho san pham |
| GROUND | Mat phang san |
| ROOM | Phong kin don gian |
| PEDESTAL | De trung bay san pham |
| GRADIENT | Nen gradient mau |

**Cach su dung:**
1. Chon tab **Scene** trong panel RECA
2. Chon kieu anh sang, camera, moi truong tu dropdown
3. Nhan **Setup Lighting** / **Setup Camera** / **Setup Environment** rieng le
4. Hoac nhan **Quick Scene Setup** de thiet lap tat ca cung luc
5. Dung **Save Preset** de luu cau hinh yeu thich, **Load Preset** de tai lai
6. Nhan **Clear Scene** de xoa tat ca va bat dau lai

---

## Module 2: Batch Processor (Xu ly hang loat)

Xu ly nhieu file 3D cung luc - chuyen doi dinh dang, rename, toi uu, render hang loat.

### Cac thao tac (Operations):

| Thao tac | Mo ta |
|----------|-------|
| CONVERT | Chuyen doi dinh dang file (VD: OBJ sang FBX, FBX sang GLB) |
| RENDER | Render tat ca file trong thu muc |
| INFO | Xuat thong tin (so vertices, faces, materials) cua moi file |
| RENAME_OBJ | Doi ten hang loat cac object trong file |
| OPTIMIZE | Toi uu mesh (loai bo duplicate vertices, recalculate normals) |
| PURGE | Don dep du lieu khong su dung (orphan data) |
| EXPORT_SEP | Xuat tung object thanh file rieng |

### Dinh dang ho tro:
`OBJ` `FBX` `GLB` `GLTF` `STL` `USD` `BLEND`

### Cach su dung:
1. Chon tab **Batch** trong panel RECA
2. Nhap **Source Directory** (thu muc chua file nguon)
3. Nhap **Output Directory** (thu muc xuat ket qua)
4. Nhap **File Pattern** (VD: `*.fbx` de chi xu ly file FBX, `*` de xu ly tat ca)
5. Chon **Operation** tu dropdown
6. Nhan **Scan Files** de quet va xem truoc danh sach file
7. Nhan **Execute Batch** de bat dau xu ly

**Luu y:** Tick **Backup** de tao ban sao luu truoc khi xu ly.

---

## Module 3: Procedural Generator (Tao hinh thu tuc)

Tu dong tao cac mo hinh 3D phuc tap tu cac tham so don gian.

### Cac loai generator:

| Loai | Mo ta | Tham so chinh |
|------|-------|---------------|
| BUILDING | Tao toa nha nhieu tang | So tang, kich thuoc, co cua so |
| TERRAIN | Tao dia hinh nui doi | Kich thuoc, do cao, do phan giai, noise |
| TREE | Tao cay | Do cao, ban kinh tan, so nhanh |
| ROCKS | Tao da | So luong, kich thuoc, do gho ghe |
| CITY | Tao thanh pho | Kich thuoc luoi, so toa nha, do cao toi da |
| ARRAY_PATTERN | Tao mang pattern | So hang/cot, khoang cach, xoay |
| SCATTER | Rai object ngau nhien tren be mat | So luong, pham vi, ti le ngau nhien |
| PIPE | Tao he thong ong | So doan, ban kinh, goc cong |

### Cach su dung:
1. Chon tab **Proc** trong panel RECA
2. Chon loai generator tu dropdown
3. Dieu chinh cac tham so (seed, kich thuoc, so luong, v.v.)
4. Nhan **Generate** de tao
5. Thay doi **Seed** de co ket qua ngau nhien khac nhau
6. Dieu chinh **Quality** (Low/Medium/High) de thay doi do chi tiet

---

## Module 4: Quick Tools (Cong cu nhanh)

Tap hop cac cong cu thao tac nhanh voi object.

### Cac chuc nang:

**Align & Distribute (Canh chinh va phan bo):**
- Chon nhieu object, chon truc (X/Y/Z), nhan **Align** de canh hang
- Nhan **Distribute** de phan bo deu cac object

**Set Origin (Dat diem goc):**
| Tuy chon | Mo ta |
|----------|-------|
| BOTTOM | Dat origin o day object (huu ich khi dat object len mat phang) |
| TOP | Dat origin o dinh |
| CENTER | Dat origin o tam |
| CURSOR | Dat origin tai vi tri 3D Cursor |

**Mirror (Doi xung):**
- Chon truc X/Y/Z, nhan **Mirror** de tao ban sao doi xung

**Random Transform (Bien doi ngau nhien):**
- Nhap gia tri ngau nhien cho Location, Rotation, Scale
- Nhan **Randomize** de ap dung - rat huu ich khi tao canh tu nhien

**Smart Select (Chon thong minh):**
| Kieu | Mo ta |
|------|-------|
| TYPE | Chon theo loai object (Mesh, Light, Camera, v.v.) |
| NAME | Chon theo ten (ho tro wildcard `*`) |
| MATERIAL | Chon theo material dang dung |
| VERTS | Chon theo so luong vertices (min-max) |
| FACES | Chon theo so luong faces |
| NO_MAT | Chon object khong co material |
| HIDDEN | Chon object dang an |

**Cac cong cu khac:**
- **Copy Attributes**: Sao chep thuoc tinh tu object active sang cac object da chon
- **Apply Transforms**: Ap dung Location/Rotation/Scale
- **Flatten Hierarchy**: Lam phang cay phan cap (xoa parent-child)
- **Merge**: Gop nhieu object thanh mot
- **Separate**: Tach object theo loose parts

---

## Module 5: Render Manager (Quan ly Render)

Quan ly render voi cac preset chuyen nghiep va tinh nang tu dong hoa.

### Render Presets:

| Preset | Do phan giai | Samples | Mo ta |
|--------|-------------|---------|-------|
| PREVIEW | 960x540 | 32 | Xem nhanh (nhanh nhat) |
| HD | 1920x1080 | 128 | Full HD |
| 2K | 2560x1440 | 256 | 2K |
| 4K | 3840x2160 | 512 | 4K (chat luong cao) |
| ULTRA | 3840x2160 | 1024 | Ultra (chat luong cao nhat) |
| CLAY | - | 64 | Clay render (chi co mau xam, khong material) |
| WIREFRAME | - | 32 | Render duong vien wireframe |
| AO | - | 64 | Ambient Occlusion only |

### Cac tinh nang:

**Quick Render:**
- Chon preset, nhan **Render** - anh se duoc luu voi ten co timestamp

**Render All Cameras:**
- Tu dong render tu tat ca camera trong scene

**Turntable:**
- Tao animation quay 360 do quanh object
- Nhap so frame, nhan **Setup Turntable**
- Sau do render animation de co video quay san pham

**Color Management:**
- Chuyen doi nhanh giua **AgX** (mac dinh Blender 4+) va **Filmic**

### Cach su dung:
1. Chon tab **Render** trong panel RECA
2. Chon render preset tu dropdown
3. Nhap duong dan luu file (Output Path)
4. Nhan **Apply Preset** de ap dung cai dat
5. Nhan **Quick Render** de render ngay
6. Hoac dung **Render All Cameras** / **Setup Turntable** cho cac nhu cau nang cao

---

## Module 6: Material Tools (Cong cu Material)

Tao va quan ly material PBR chuyen nghiep.

### 20 Material Presets co san:

| Nhom | Presets |
|------|---------|
| Kim loai | Metal Gold, Metal Silver, Metal Copper, Metal Brushed |
| Kinh | Glass Clear, Glass Frosted, Glass Colored |
| Nhua | Plastic Glossy, Plastic Matte |
| Go | Wood Polished, Wood Rough |
| Da | Stone Marble, Stone Granite |
| Vai | Fabric Silk, Fabric Cotton |
| Dac biet | Skin (SSS), Neon (Emission), Holographic, Ceramic, Rubber |

### Cac chuc nang:

**Apply Preset Material:**
1. Chon object
2. Chon preset tu dropdown
3. Nhan **Apply Material**

**Custom Material Builder:**
- Tuy chinh Base Color, Metallic, Roughness, IOR, Transmission, Emission
- Tuy chon them Noise Texture de tao hieu ung tu nhien
- Nhan **Create Custom Material**

**Random Materials:**
- Tao material ngau nhien cho nhieu object cung luc
- Dieu chinh pham vi Hue, Saturation, Value
- Huu ich khi tao nhieu object mau sac da dang

**Replace Material:**
- Thay the mot material bang material khac tren tat ca object

**Bake to Vertex Colors:**
- Chuyen material thanh vertex colors (huu ich khi export sang game engine)

---

## Module 7: MCP Server (AI dieu khien Blender)

Cho phep AI (Claude Code, OpenClaw.ai, Cursor, Codex) dieu khien Blender tu xa qua giao thuc MCP.

### Cach thiet lap:

**Buoc 1: Bat MCP Server trong Blender**
1. Chon tab **MCP** trong panel RECA
2. Cau hinh **Port** (mac dinh: `9876`)
3. Nhan **Start Server**
4. Trang thai se hien **Running** voi dau xanh

**Buoc 2: Cau hinh AI Client**

**Cho Claude Code / Claude Desktop:**
Them vao file cau hinh MCP (`~/.claude/mcp.json` hoac `claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "blender-reca": {
      "url": "http://127.0.0.1:9876"
    }
  }
}
```

**Cho OpenClaw.ai:**
Them vao cau hinh MCP cua OpenClaw:
```json
{
  "mcpServers": {
    "blender-reca": {
      "url": "http://127.0.0.1:9876"
    }
  }
}
```

**Cho Cursor:**
Vao `Settings > MCP Servers > Add Server`:
- Name: `blender-reca`
- URL: `http://127.0.0.1:9876`

**Buoc 3: Su dung**
Sau khi ket noi, ban co the yeu cau AI thuc hien cac tac vu trong Blender bang ngon ngu tu nhien:
- *"Tao mot khoi lap phuong mau do"*
- *"Setup studio lighting"*
- *"Render scene o 4K"*
- *"Tao mot toa nha 10 tang"*

### 16 MCP Tools:

| Tool | Mo ta | Vi du su dung |
|------|-------|---------------|
| `scene_info` | Lay thong tin scene hien tai | Xem so object, render settings |
| `list_objects` | Liet ke tat ca object | Xem danh sach object trong scene |
| `add_object` | Them object moi | Them Cube, Sphere, Cylinder, v.v. |
| `delete_object` | Xoa object | Xoa object theo ten |
| `transform_object` | Di chuyen/xoay/co dan object | Dat vi tri, xoay, thay doi kich thuoc |
| `set_material` | Gan material cho object | Dat mau sac, metallic, roughness |
| `render` | Render scene | Render va luu anh |
| `import_model` | Import file 3D | Import OBJ, FBX, GLB, STL |
| `export_model` | Export file 3D | Export sang cac dinh dang |
| `execute_python` | Chay code Python trong Blender | Thuc thi bpy script bat ky |
| `setup_scene` | Thiet lap scene nhanh | Dat lighting, camera, environment |
| `generate_procedural` | Tao mo hinh thu tuc | Tao building, terrain, tree, v.v. |
| `add_modifier` | Them modifier | Them Subdivision, Bevel, Boolean, v.v. |
| `add_light` | Them den | Them Point, Sun, Spot, Area light |
| `add_camera` | Them camera | Them camera moi voi cac thong so |
| `keyframe` | Dat keyframe animation | Tao animation cho object |

### Kiem tra ket noi:
- Truy cap `http://127.0.0.1:9876/health` trong trinh duyet - neu tra ve JSON la server dang chay
- Truy cap `http://127.0.0.1:9876/tools` de xem danh sach tools

---

## Module 8: AI Integration (Tich hop AI)

Dung AI de tao scene, viet script, va dieu khien Blender bang ngon ngu tu nhien ngay trong Blender.

### 6 AI Providers:

| Provider | Mo ta | Yeu cau |
|----------|-------|---------|
| **OpenClaw.ai** | AI chuyen dung cho 3D | API Key tu openclaw.ai |
| **Google Antigravity** | Google Gemini/Antigravity | API Key tu Google AI Studio |
| **Anthropic Claude** | Claude AI (Anthropic) | API Key tu console.anthropic.com |
| **OpenAI** | GPT-4 / ChatGPT | API Key tu platform.openai.com |
| **Local (Ollama)** | AI chay local khong can internet | Cai Ollama + model (VD: llama3) |
| **Custom** | Tu cau hinh endpoint bat ky | URL va API Key tu cung cap |

### Cach thiet lap:

**Buoc 1: Chon Provider**
1. Chon tab **AI** trong panel RECA
2. Chon AI Provider tu dropdown
3. Nhap **API Key** (tru Ollama local khong can)

**Buoc 2: Chon Context (Ngu canh)**
| Context | AI se tap trung vao |
|---------|---------------------|
| SCENE | Xay dung va bo cuc scene |
| MATERIAL | Tao va chinh sua material |
| MODELING | Mo hinh hoa va chinh sua mesh |
| LIGHTING | Thiet lap anh sang |
| ANIMATION | Tao animation va keyframe |
| CAMERA | Thiet lap camera va goc quay |
| SCRIPT | Viet Python script cho Blender |

**Buoc 3: Su dung**
- Nhap prompt (yeu cau) vao o text
- Nhan **Send to AI**
- AI se tra ve code Python va tu dong thuc thi trong Blender

### 6 Quick Prompts (Prompt nhanh):
Nhan mot nut de tao ngay:
1. **Product Scene** - Scene trung bay san pham chuyen nghiep
2. **Low Poly Landscape** - Phong canh low poly
3. **Room Interior** - Noi that phong
4. **Space Scene** - Canh khong gian vu tru
5. **Character Pose** - Pose nhan vat co ban
6. **Arch Viz** - Kien truc visualization

### Prompt History (Lich su):
- Tat ca cac prompt da gui duoc luu lai
- Chon tu danh sach de su dung lai
- Xem ket qua truoc do

### Meo su dung:
- Viet prompt cu the: *"Tao mot ban ghe go voi 4 chan, dat tren san go, co den spotlight chieu tu tren xuong"*
- Chon dung Context de AI hieu ro hon ban muon lam gi
- Dung Ollama (Local) neu ban khong muon gui du lieu len cloud
- Ket hop voi MCP Server de AI ben ngoai (Claude Code) cung co the dieu khien

---

## Phim tat & Meo

- Nhan **N** de mo/dong Sidebar trong Viewport
- Tab **RECA** nam trong Sidebar
- Tat ca thao tac co the **Undo** bang `Ctrl+Z`
- Dung **Clear Scene** (tab Scene) de bat dau lai tu dau
- Tat ca file render duoc luu voi **timestamp** de khong ghi de
- **Seed** trong Procedural Generator: cung seed = cung ket qua (de tai tao)

## Xu ly loi thuong gap

| Loi | Cach xu ly |
|-----|------------|
| Panel RECA khong hien | Nhan `N` de mo Sidebar, tim tab RECA |
| MCP Server khong start | Kiem tra port 9876 co bi chiem chua, doi port khac |
| AI khong tra loi | Kiem tra API Key da nhap dung, kiem tra ket noi internet |
| Render bi den | Kiem tra co light trong scene khong, dung Setup Lighting |
| Procedural bi loi | Thu thay doi Seed hoac giam Quality |
| Batch khong tim thay file | Kiem tra duong dan thu muc va file pattern |

---

## Requirements

- Blender 5.1.0+
- No external Python dependencies (uses only stdlib + bpy)
- For AI Integration: API key from your chosen provider (except Ollama local)
- For MCP Server: port 9876 available (configurable)

## License

GPL-3.0-or-later
