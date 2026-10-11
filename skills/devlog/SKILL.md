---
name: devlog
description: Claude Code ile hangi projede ne geliştirildiğinin günlük özeti ve her projede en son ne yapıldığı. Kullanıcı "bugün ne yaptık", "günlük özet", "dün neler geliştirildi", "bu hafta", "X projesinde en son ne yapıldı", "devlog" dediğinde kullan.
argument-hint: "[bugün|dün|YYYY-MM-DD|7g|son [proje]]"
allowed-tools: Bash(python3 -I *), Read, Write
---

# devlog

Veri kaynağı: `~/.claude/projects` altındaki tüm Claude Code transcript'leri (T3, terminal, subagent'lar dahil).
Stop hook her turdan sonra oturumu `~/.claude/devlog/sessions/` altına arşivler; script her çalıştığında
değişmiş tüm transcript'leri yeniden tarar. Transcript silinse bile arşiv kalır.

## Adımlar

1. Argümanı script argümanına çevir:
   - boş / `bugün` → `today`; `dün` → `yesterday`; `YYYY-MM-DD` → aynen
   - `son` → `last`; `son <proje>` → `last <proje>`
   - `7g`, `hafta`, N gün: ham çıktı çok büyük (günde 30-100 KB), tek seferde okuma. Her gün için
     `~/.claude/devlog/daily/<tarih>.md` varsa ve gün bugün değilse onu kullan; yoksa o günü aşağıdaki
     adımlarla özetleyip kaydet. Sonra günlük özetlerden haftalık özet çıkar.
2. Çalıştır ve dosyaya yaz, sonra Read ile oku (büyükse offset/limit ile parça parça):
   `python3 -I "${CLAUDE_SKILL_DIR}/devlog.py" <arg> > ~/.claude/devlog/last-raw.md`
3. Ham kaydı okunur bir özete çevir. Kullanıcıya şunu göster:
   - Proje başına bir başlık (en son çalışılan proje en üstte), yanında son çalışma saati.
   - Altında 2-5 madde: **ne yapıldı / ne bitti** (sonuç odaklı, dosya listesi değil). Commit ve PR varsa belirt.
   - Yarım kalan ya da kullanıcıdan onay/bilgi bekleyen işleri ayrı "Açık kalanlar" bölümünde topla.
   - Gürültüyü at: `/tmp`, test amaçlı kısa sohbetler, sadece soru-cevap olan ve iş üretmeyen oturumlar ("ok", kod kelimesi testi vb.).
   - `last` modunda proje başına tek satırlık "en son ne yapıldı" + tarih yeterli.
4. Gün raporlarında (`today`/`yesterday`/tarih) özeti `~/.claude/devlog/daily/<YYYY-MM-DD>.md` dosyasına da yaz (varsa üzerine yaz).

Kullanıcının dilinde yaz. Ham kayıttaki istekleri olduğu gibi kopyalama; ne yapıldığını anlat.
