#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка презентации nbody_deepseek.pptx (12 слайдов, 16:9, тёмная тема)."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor

BASE = "/home/kds/sci/gadget2_docker/nbody/presentations/2026-09-10"
OUT = BASE + "/nbody_deepseek.pptx"

BG = RGBColor(0x0B, 0x1F, 0x3A)
ACC = RGBColor(0x4F, 0xC3, 0xF7)
TXT = RGBColor(0xE8, 0xEE, 0xF6)
DIM = RGBColor(0xA9, 0xBF,  0xDD)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def new_slide():
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    return s


def add_title(s, text):
    box = s.shapes.add_textbox(Inches(0.45), Inches(0.25), Inches(12.45), Inches(0.85))
    tf = box.text_frame; tf.word_wrap = True
    r = tf.paragraphs[0].add_run()
    r.text = text
    r.font.size = Pt(27); r.font.bold = True; r.font.color.rgb = ACC; r.font.name = "Calibri"
    line = s.shapes.add_shape(1, Inches(0.5), Inches(1.08), Inches(12.35), Emu(19050))
    line.fill.solid(); line.fill.fore_color.rgb = ACC; line.line.fill.background()


def add_bullets(s, items, top=Inches(1.45), left=Inches(0.70), width=Inches(11.95),
                height=Inches(5.4), size=17):
    box = s.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame; tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(12)
        r = p.add_run(); r.text = "•  " + it
        r.font.size = Pt(size); r.font.color.rgb = TXT; r.font.name = "Calibri"


def add_caption(s, text):
    box = s.shapes.add_textbox(Inches(0.45), Inches(5.28), Inches(12.45), Inches(0.4))
    tf = box.text_frame; p = tf.paragraphs[0]
    r = p.add_run(); r.text = text
    r.font.size = Pt(11); r.font.italic = True; r.font.color.rgb = DIM; r.font.name = "Calibri"


def add_picture_fit(s, path, left, top, max_w, max_h):
    pic = s.shapes.add_picture(path, left, top)
    w, h = pic.width, pic.height
    scale = min(max_w / w, max_h / h)
    pic.width = int(w * scale); pic.height = int(h * scale)
    pic.left = left + int((max_w - pic.width) / 2)
    pic.top = top + int((max_h - pic.height) / 2)


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


# ---------- Слайд 1: титул ----------
s = new_slide()
box = s.shapes.add_textbox(Inches(0.9), Inches(2.2), Inches(11.5), Inches(1.8))
tf = box.text_frame; tf.word_wrap = True
r = tf.paragraphs[0].add_run()
r.text = "От CDM к dSIDM: поиск тёмного диска в карликовых галактиках"
r.font.size = Pt(38); r.font.bold = True; r.font.color.rgb = TXT; r.font.name = "Calibri"
box2 = s.shapes.add_textbox(Inches(0.9), Inches(4.0), Inches(11.5), Inches(1.2))
r2 = box2.text_frame.paragraphs[0].add_run()
r2.text = "Может ли диссипативная тёмная материя создать вращающуюся структуру?"
r2.font.size = Pt(21); r2.font.color.rgb = ACC; r2.font.name = "Calibri"
box3 = s.shapes.add_textbox(Inches(0.9), Inches(5.5), Inches(11.5), Inches(0.6))
r3 = box3.text_frame.paragraphs[0].add_run()
r3.text = "Численные симуляции SIDM и dSIDM  •  сентябрь 2026"
r3.font.size = Pt(14); r3.font.color.rgb = DIM; r3.font.name = "Calibri"
notes(s, "Доклад о том, может ли диссипативная тёмная материя сформировать тёмный диск в карликовых галактиках. Логика: CDM-контроль → упругий SIDM → диссипативный dSIDM → тест с высоким спином.")

# ---------- Слайд 2: постановка задачи ----------
s = new_slide()
add_title(s, "Постановка задачи")
add_bullets(s, [
    "Наблюдаемые карликовые галактики расходятся с предсказаниями CDM: в центрах — пологие ядра, а не крутые каспы, и нет выраженных вращающихся структур.",
    "Идея: если частицы тёмной материи рассеиваются и при столкновениях теряют энергию (диссипативная SIDM, dSIDM), гало может «остывать» и сплющиваться.",
    "Вопрос исследования: способна ли dSIDM сформировать вращающийся тёмный диск — или центральный коллапс и численные патологии наступят раньше?",
    "Метод: серия N-body симуляций изолированного карликового гало с упругим (SIDM) и неупругим (dSIDM) самовзаимодействием, N = 1e5–1e6.",
], size=18)
notes(s, "Ключевая научная развилка: CDM предсказывает каспы, наблюдения показывают ядра. Задача — проверить, способна ли диссипация создать тёмный диск.")

# ---------- Слайд 3: CDM ----------
s = new_slide()
add_title(s, "CDM: базовая линия")
add_picture_fit(s, BASE + "/images/s03_cdm_density_profiles.png", Inches(0.5), Inches(1.35), Inches(12.35), Inches(3.75))
add_caption(s, "Профили плотности CDM-контроля и SIDM в сравнении с NFW-фитом")
add_bullets(s, [
    "Исходная модель: изолированное NFW-гало, масштабный радиус r_s ≈ 4.9 кпк; контроль N = 1e6, обзорные прогоны N = 1e5.",
    "CDM сохраняет сферическое равновесие и крутой центральный профиль — эталон для всех сравнений.",
], top=Inches(5.75), height=Inches(1.55), size=14)
notes(s, "Численный контроль: CDM-профиль совпадает с NFW. Это базовая линия для всех дальнейших сравнений.")

# ---------- Слайд 4: SIDM ----------
s = new_slide()
add_title(s, "Упругий SIDM: ядро вместо каспа")
add_picture_fit(s, BASE + "/images/s04_sidm_ninteractions_radial.png", Inches(0.5), Inches(1.35), Inches(12.35), Inches(3.75))
add_caption(s, "Радиальный профиль числа рассеяний на частицу и доля затронутых частиц; σ =  20 см²/г")
add_bullets(s, [
    "Сечение упругого рассеяния σ = 0.1 / 1 /  5 / 20 см²/г.",
    "Полный прогон σ = 20, N = 1e6, до T = 5: 8.15 млн рассеяний, затронуто  51% частиц.",
    "Чем больше σ, тем мягче центральное ядро (core вместо cusp) — известный эффект воспроизводится количественно.",
], top=Inches(5.75), height=Inches(1.55), size=13)
notes(s, "Верификация SIDM-модуля: прогон σ = 20 даёт 8.15 млн рассеяний и 51% затронутых частиц. Эффект ядра воспроизводится корректно.")
# ---------- Слайд 5: dSIDM ----------
s = new_slide()
add_title(s, "dSIDM: диссипация и сетка экспериментов")
add_bullets(s, [
    "При неупругом столкновении часть кинетической энергии уносится. Управляемые параметры: фактор диссипации f (доля потерь D) и характерный отскок.",
    "Логика: диссипация «выстуживает» центральные области и должна усиливать вращательную поддержку.",
    "Сетка: σ =  1 /  5 /  10 см2/г × f =  0.05 /  0.1 /  0.2 —  11 прогонов(N =  1e5, T =  2 и   5).",
    "Критерии оценки: форма(c/a, z_rms/R_rms) и вращательная поддержка |Vrot|/σ, профили плотности, численная стабильность.",
], size=18)
notes(s, "Описание физической модели диссипации и сетки экспериментов. Сканируются и сечение, и доля диссипации, чтобы отделить физику от численных артефактов.")

# ---------- Слайд 6: морфология ----------
s = new_slide()
add_title(s, "Морфология: тёмного диска не видно")
add_picture_fit(s, BASE + "/images/s06_morphology_montage.png", Inches(0.5), Inches(1.35), Inches(12.35), Inches(3.75))
add_caption(s, "Поверхностная плотность: CDM, SIDM, dSIDM; верхний ряд — face-on, нижний — edge-on")
add_bullets(s, [
    "Ни в одном сценарии при слабом начальном вращении(k ≈  0.15, тонкой дисковой компоненты в edge-on не видно.",
    "У dSIDM есть центральная концентрация, но геометрия остаётся пухлой, сфероидальной.",
], top=Inches(5.75), height=Inches(1.55), size=14)
notes(s, "Главный визуальный слайд. В edge-on проекции диск выглядел бы как тонкая полоса; здесь все сценарии показывают шарообразное гало.")

# ---------- Слайд 7: форма ----------
s = new_slide()
add_title(s, "Форма: сфероид, а не диск")
add_picture_fit(s, BASE + "/images/s07_shape_no_disk.png", Inches(0.5), Inches(1.35), Inches(12.35), Inches(3.75))
add_caption(s, "Радиальные профили b/a, c/a, z_rms/R_rms и вращательной поддержки |Vrot|/σ для CDM / SIDM / dSIDM")
add_bullets(s, [
    "При r <  5 кпк: c/a ≈  0.94, z/R ≈  0.67, |Vrot|/σ ≈  0.07. Для диска нужно c/a <  0.75 и |Vrot|/σ >  0.15.",
    "Диссипация почти не уплощает гало и не создаёт вращательной поддержки: диск-скоре =  0 во всех конфигурациях.",
], top=Inches(5.75), height=Inches(1.55), size=14)
notes(s, "Количественное подтверждение: все метрики формы далеко от дисковых. Диссипация действительно охлаждает материю, но вращательной поддержки почти не появляется.")

# ---------- Слайд 8: профили плотности ----------
s = new_slide()
add_title(s, "Профили плотности: ядро без диска")
add_picture_fit(s, BASE + "/images/s08_log_rho_profiles.png", Inches(0.5), Inches(1.35), Inches(12.35), Inches(3.75))
add_caption(s, "Профили плотности в логарифмической шкале(верх) и разность относительно CDM(низ)")
add_bullets(s, [
    "SIDM σ =  10 заметно смягчает центр: Δlog ρ ≈ − 0.9 на малых радиусах.",
    "dSIDM следуют тому же тренду; значимой дополнительной центральной контракции сверх SIDM отслеживается.",
], top=Inches(5.75), height=Inches(1.55), size=14)
notes(s, "Диссипация не создаёт дополнительного сжатия центра относительно упругого SIDM. Эффект ядра — в основном заслуга упругих рассеяний.")

# ---------- Слайд 9: патология ----------
s = new_slide()
add_title(s, "Новая патология: runaway рассеяний")
add_picture_fit(s, BASE + "/images/s09_ni_collapse_pathology.png", Inches(0.5), Inches(1.35), Inches(12.35), Inches(3.75))
add_caption(s, "Эволюция темпа рассеяний(число взаимодействий на снапшот) для σ =  10 при разных факторах диссипации")
add_bullets(s, [
    "При f ≥  0.1 темп рассеяний к концу прогона становится взрывным(~3e7 за снапшот,, шаг времени коллапсирует около t ≈  4.7 — раньше, чем мог бы сформироваться диск.",
    "Стабильна только слабая диссипация f =  0.05 — но и она диска не даёт.",
], top=Inches(5.75), height=Inches(1.55), size=13)
notes(s, "Это численная патология, а не физика: рост темпа рассеяний и коллапс шага времени. Сильная диссипация не успевает создать диск до того, как симуляция ломается.")

# ---------- Слайд 10: кампания k = 0.8 ----------
s = new_slide()
add_title(s, "Новая кампания: высокий спин гало(k =  0.8)")
add_picture_fit(s, BASE + "/images/s10_grid_ca_evolution.png", Inches(0.45), Inches(1.35), Inches(6.05), Inches(3.7))
add_picture_fit(s, BASE + "/images/s10_grid_vrot_evolution.png", Inches(6.85), Inches(1.35), Inches(6.05), Inches(3.7))
add_caption(s, "Эволюция c/a(слева) и |Vrot|/σ(справа) по кампании для разных диссипативных коэффициентов")
add_bullets(s, [
    "Гипотеза: значительный начальный спин гало может помочь диссипации перейти к вращающейся структуре.",
    "Сетка:  6 прогонов(N =  1e5, T =  2): CDM-контроль, упругий SIDM σ =  2.5 и dSIDM с D =  0.10 /  0.25 /  0.50 /  0.75.",
    "Все  6 прогонов завершены, анализ в процессе.",
], top=Inches(5.75), height=Inches(1.55), size=13)
notes(s, "Промежуточный статус: высокий спин — новый параметр. Пока завершены только прогоны; ключевой вопрос — появится ли вращательная поддержка при больших D.")

# ---------- Слайд 11: планы ----------
s = new_slide()
add_title(s, "Планы")
add_bullets(s, [
    "Полный анализ кампании k =  0.8: классификация каждого прогона по критериям диска(z_rms/R_rms <  0.55, c/a <  0.75, |Vrot|/σ >  0.15).",
    "Продлённые прогоны до T =  5 для лучших кандидатов.",
    "Двухкомпонентные гало(CDM + dSIDM) и более высокие сечения σ.",
    "Аудит физики диссипации: сохранение энергии и импульса при неупругих столкновениях, корректность темпа рассеяний.",
], size=18)
notes(s, "Следующие шаги: сначала полностью разобрать кампанию k =  0.8, затем продлить лучших кандидатов. Также стоит проверить физикуна уровне исходного кода.")

# ---------- Слайд 12: выводы ----------
s = new_slide()
add_title(s, "Выводы")
add_bullets(s, [
    "Конвейер симуляций CDM → SIDM → dSIDM построен и верифицирован(N до  1e6).",
    "Упругий SIDM подтверждает смягчение центрального каспа — появляется ядро.",
    "Ни упругий, ни диссипативный сценарий при слабом начальном вращении(k ≈  0.15) не дают диска: c/a ≈  0.94, |Vrot|/σ ≈  0.07.",
    "Сильная диссипация(f ≥  0.1) упираетсяв численный коллапс раньше, чем образуется диск.",
    "Решающий тест: высокий спин(k =  0.8) — прогоны завершены, анализ в процессе.",
], size=17)
notes(s, "Итог: ни упругий SIDM, ни dSIDM при слабом вращении не создают диск; сильная диссипация ломает симуляцию. Главный открытый вопрос— поможет ли высокий спин гало.")

prs.save(OUT)
print("Saved:", OUT)
