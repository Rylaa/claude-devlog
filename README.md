# claude-devlog

Claude Code ile her gün hangi projede ne geliştirildiğini okunur bir özet olarak verir. Her projede en son ne yapıldığını da tek komutla gösterir.

- **Hiçbir şey kaçmaz.** Kaynak, Claude Code'un tüm oturum kayıtları (`~/.claude/projects`). Terminal, Desktop, SDK ile çalışan uygulamalar ve subagent'lar buna dahil.
- **Sürekli güncel.** Her cevaptan sonra arka planda çalışan bir Stop hook oturumun kısa özetini `~/.claude/devlog/sessions/` altına arşivler. Her rapor öncesinde değişmiş tüm kayıtlar yeniden taranır, yani hook bir şeyi kaçırsa bile rapor tam çıkar.
- **Kalıcı.** Claude Code eski oturum kayıtlarını silse bile arşiv kalır.
- **Commit'ler git'ten gelir.** `git log` ile, yalnızca senin e-postanla yapılanlar.

## Kurulum

```
/plugin marketplace add Rylaa/claude-devlog
/plugin install devlog@claude-devlog
```

Gereken tek şey `python3` (3.9+). Harici bağımlılık yok.

## Kullanım

| Komut | Ne verir |
|---|---|
| `/devlog:devlog` | Bugünün özeti: proje proje ne yapıldı, ayrıca açık kalanlar |
| `/devlog:devlog dün` · `/devlog:devlog 2026-10-09` | Belirli bir günün özeti |
| `/devlog:devlog hafta` | Son 7 gün, günlük özetlerden toplanır |
| `/devlog:devlog son` | Her projede en son ne yapıldı |
| `/devlog:devlog son <proje>` | Tek bir projenin son durumu |

"Bugün ne yaptık?" ya da "X projesinde en son ne yapıldı?" diye sormak da yeterli.

Günlük özetler `~/.claude/devlog/daily/<tarih>.md` dosyasına kaydedilir.

Ham rapor, Claude'suz, terminalden de alınabilir:

```
python3 skills/devlog/devlog.py today      # yesterday | 2026-10-09 | 7d | last [proje] | sync
```

## Nasıl çalışır

`skills/devlog/devlog.py` her oturum kaydından kullanıcı isteklerini, Claude'un son cevabını, düzenlenen dosyaları, commit'leri ve PR'ları çıkarır. Bunları oturum başına küçük bir JSON olarak arşivler. Rapor arşivden gün ve proje bazında üretilir. Worktree'ler ana reponun adı altında toplanır. Aynı şablonla başlayan, tekrarlı ve tek seferlik otomasyon çağrıları (`claude -p` ile çalışan yargıç ya da sınıflandırıcı gibi) gizlenir, raporda yalnızca sayıları gösterilir.

Test: `python3 skills/devlog/test_devlog.py`
