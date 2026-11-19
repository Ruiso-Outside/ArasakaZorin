// ARASAKA FX // efeitos visuais do tema Arasaka para o GNOME Shell (45+).
//
//   janelas    glitch ao abrir e fechar (aberração cromática, fatias deslocadas, linhas de varredura) na GPU
//   visão      glitch ao abrir a visão geral (tecla Super)
//   fundo      feixe de varredura vermelho que passa pelo papel de parede, com "falhas" de vez em quando
//   crt        linhas de varredura e vinheta bem leves por cima de tudo; somem sozinhas em tela cheia (jogos, vídeos)
//
// Configuração: ~/.config/arasaka/fx.json  { "windows": true, "overview": true, "background": true, "crt": true }
// O comando arasaka-fx muda esse arquivo, e a extensão aplica na hora (sem sair da sessão).

import Cairo from 'cairo';
import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const DEFAULTS = {windows: true, overview: true, background: true, crt: true};
const CONFIG = GLib.build_filenamev([GLib.get_user_config_dir(), 'arasaka', 'fx.json']);
const HOOK = Cogl.SnippetHook ? Cogl.SnippetHook.FRAGMENT : Shell.SnippetHook.FRAGMENT;

// ---------------------------------------------------------------- shader do glitch
const GLITCH_DECL = `
  uniform sampler2D uTexture;
  uniform float uAmount;   // 0 = imagem normal, 1 = glitch máximo
  uniform float uSeed;
  float hash(float n) { return fract(sin(n) * 43758.5453); }
`;
const GLITCH_CODE = `
  vec2 uv = cogl_tex_coord_in[0].st;
  float a = uAmount;
  // fatias horizontais que pulam para os lados
  float band = floor(uv.y * 28.0);
  float r = hash(band * 13.7 + uSeed);
  float shift = (r > 0.62 ? (hash(band + uSeed * 3.1) - 0.5) * 0.09 : 0.0) * a;
  vec2 p = vec2(uv.x + shift, uv.y);
  // aberração cromática: vermelho e ciano separados
  float ca = 0.012 * a;
  vec4 base = texture2D(uTexture, p);
  vec4 c;
  c.r = texture2D(uTexture, p + vec2(ca, 0.0)).r;
  c.g = base.g;
  c.b = texture2D(uTexture, p - vec2(ca, 0.0)).b;
  c.a = max(base.a, max(texture2D(uTexture, p + vec2(ca, 0.0)).a, texture2D(uTexture, p - vec2(ca, 0.0)).a));
  // linhas de varredura e um véu vermelho
  float scan = 0.82 + 0.18 * sin(uv.y * 900.0);
  c.rgb *= mix(1.0, scan, a);
  c.rgb = mix(c.rgb, vec3(1.0, 0.08, 0.1) * c.a, 0.16 * a);
  // pedaços que somem (fica só o contorno da fatia)
  if (r > 0.93 && a > 0.35) c *= 0.15;
  cogl_color_out = c * cogl_color_in.a;
`;

const GlitchEffect = GObject.registerClass({
    Properties: {
        'amount': GObject.ParamSpec.double('amount', '', '', GObject.ParamFlags.READWRITE, 0, 1, 0),
    },
}, class GlitchEffect extends Shell.GLSLEffect {
    _init() {
        super._init();
        this._seed = Math.random() * 100;
        this.connect('notify::amount', () => this.queue_repaint());
    }

    vfunc_build_pipeline() {
        this.add_glsl_snippet(HOOK, GLITCH_DECL, GLITCH_CODE, false);
    }

    vfunc_paint_target(node, ctx) {
        this.set_uniform_float(this.get_uniform_location('uTexture'), 1, [0]);
        this.set_uniform_float(this.get_uniform_location('uAmount'), 1, [this.amount]);
        this.set_uniform_float(this.get_uniform_location('uSeed'), 1, [this._seed + Math.floor(this.amount * 6)]);
        super.vfunc_paint_target(node, ctx);
    }
});

// Glitch passageiro num ator: começa em "from", vai a "to" em "ms" e sai sozinho
function glitch(actor, {ms = 320, from = 1, to = 0} = {}) {
    if (!actor || actor._arasakaGlitch)
        return;
    const fx = new GlitchEffect();
    fx.amount = from;
    actor._arasakaGlitch = fx;
    actor.add_effect_with_name('arasaka-glitch', fx);
    const tl = new Clutter.Timeline({actor, duration: ms});
    const stop = () => {
        tl.stop();
        if (actor._arasakaGlitch === fx) {
            delete actor._arasakaGlitch;
            try {
                actor.remove_effect(fx);
            } catch {
                // o ator já foi destruído
            }
        }
    };
    tl.connect('new-frame', () => {
        const t = tl.get_progress();
        // tremida: o efeito "pisca" enquanto diminui
        const flick = 0.75 + 0.25 * Math.sin(t * 40);
        fx.amount = Math.max(0, Math.min(1, (from + (to - from) * t) * flick));
    });
    tl.connect('completed', stop);
    actor.connect('destroy', () => tl.stop());
    tl.start();
}

// ---------------------------------------------------------------- fundo: feixe de varredura e falhas
const BackgroundFx = GObject.registerClass(class BackgroundFx extends St.Widget {
    _init(monitor) {
        super._init({style_class: 'arasaka-fx-bg', reactive: false, clip_to_allocation: true});
        this.set_position(monitor.x, monitor.y);
        this.set_size(monitor.width, monitor.height);
        this._h = monitor.height;
        // feixe: duas metades em degradê (o St só faz degradê de duas cores)
        this._beam = new St.Widget({reactive: false});
        const bh = Math.round(monitor.height * 0.16);
        const top = new St.Widget({style_class: 'arasaka-fx-beam-top', width: monitor.width, height: bh});
        const line = new St.Widget({style_class: 'arasaka-fx-beam-line', width: monitor.width, height: 2, y: bh});
        const bot = new St.Widget({style_class: 'arasaka-fx-beam-bottom', width: monitor.width, height: Math.round(bh / 3), y: bh + 2});
        this._beam.add_child(top);
        this._beam.add_child(line);
        this._beam.add_child(bot);
        this._beamH = bh + 2 + Math.round(bh / 3);
        this.add_child(this._beam);
        this._beam.translation_y = -this._beamH;
        this._timers = [];
        this._sweep();
        this._scheduleFault();
    }

    _later(ms, fn) {
        const id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
            this._timers = this._timers.filter(t => t !== id);
            fn();
            return GLib.SOURCE_REMOVE;
        });
        this._timers.push(id);
    }

    _sweep() {
        this._beam.translation_y = -this._beamH;
        this._beam.ease({
            translation_y: this._h,
            duration: 5200,
            mode: Clutter.AnimationMode.EASE_IN_OUT_SINE,
            onComplete: () => this._later(4000 + Math.random() * 7000, () => this._sweep()),
        });
    }

    // "falha": algumas faixas vermelhas aparecem e somem em menos de meio segundo
    _scheduleFault() {
        this._later(9000 + Math.random() * 14000, () => {
            const n = 2 + Math.floor(Math.random() * 4);
            for (let i = 0; i < n; i++) {
                const h = 2 + Math.floor(Math.random() * 18);
                const f = new St.Widget({
                    style_class: 'arasaka-fx-fault', reactive: false,
                    width: Math.round(this.width * (0.2 + Math.random() * 0.8)), height: h,
                    x: Math.round(Math.random() * this.width * 0.4), y: Math.round(Math.random() * (this._h - h)),
                    opacity: 0,
                });
                this.add_child(f);
                f.ease({
                    opacity: 255, duration: 60, mode: Clutter.AnimationMode.LINEAR,
                    onComplete: () => f.ease({
                        opacity: 0, translation_x: (Math.random() - 0.5) * 60, duration: 260 + Math.random() * 200,
                        mode: Clutter.AnimationMode.EASE_OUT_QUAD, onComplete: () => f.destroy(),
                    }),
                });
            }
            this._scheduleFault();
        });
    }

    vfunc_destroy() {
        for (const id of this._timers)
            GLib.source_remove(id);
        this._timers = [];
        this._beam.remove_all_transitions();
        super.vfunc_destroy();
    }
});

// ---------------------------------------------------------------- CRT: linhas de varredura + vinheta (desenho fixo)
const CrtFx = GObject.registerClass(class CrtFx extends St.DrawingArea {
    _init(monitor) {
        super._init({reactive: false, can_focus: false, track_hover: false});
        this.set_position(monitor.x, monitor.y);
        this.set_size(monitor.width, monitor.height);
    }

    vfunc_repaint() {
        const cr = this.get_context();
        const [w, h] = this.get_surface_size();
        cr.setOperator(Cairo.Operator.CLEAR);
        cr.paint();
        cr.setOperator(Cairo.Operator.OVER);
        cr.setSourceRGBA(0, 0, 0, 0.10);
        for (let y = 0; y < h; y += 3)
            cr.rectangle(0, y, w, 1);
        cr.fill();
        // vinheta nos cantos
        const grad = new Cairo.RadialGradient(w / 2, h / 2, Math.min(w, h) * 0.45, w / 2, h / 2, Math.max(w, h) * 0.75);
        grad.addColorStopRGBA(0, 0, 0, 0, 0);
        grad.addColorStopRGBA(1, 0, 0, 0, 0.28);
        cr.setSource(grad);
        cr.paint();
        cr.$dispose();
    }
});

// ---------------------------------------------------------------- extensão
export default class ArasakaFx extends Extension {
    enable() {
        this._cfg = this._readConfig();
        this._sig = [];
        this._bg = [];
        this._crt = [];
        this._sig.push([global.window_manager, global.window_manager.connect('map', (_w, actor) => this._onMap(actor))]);
        this._sig.push([global.window_manager, global.window_manager.connect('destroy', (_w, actor) => this._onDestroy(actor))]);
        this._sig.push([Main.overview, Main.overview.connect('showing', () => this._onOverview())]);
        this._sig.push([Main.layoutManager, Main.layoutManager.connect('monitors-changed', () => this._rebuild())]);
        // vigia a pasta (o arquivo pode ainda não existir, e o arasaka-fx o regrava inteiro)
        const dir = GLib.path_get_dirname(CONFIG);
        GLib.mkdir_with_parents(dir, 0o700);
        this._monitor = Gio.File.new_for_path(dir).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, null);
        this._monitor.connect('changed', (_m, file, other) => {
            const names = [file, other].filter(Boolean).map(f => f.get_basename());
            if (!names.includes('fx.json'))
                return;
            const cfg = this._readConfig();
            if (JSON.stringify(cfg) === JSON.stringify(this._cfg))
                return;
            this._cfg = cfg;
            this._rebuild();
        });
        this._rebuild();
        // logo Arasaka no botão do menu do Zorin (as outras extensões podem carregar depois desta)
        this._branded = new Map();
        this._sig.push([Main.extensionManager, Main.extensionManager.connect('extension-state-changed', () => this._brandSoon())]);
        this._brandSoon();
        this._selfTest();
    }

    disable() {
        for (const [obj, id] of this._sig)
            obj.disconnect(id);
        this._sig = [];
        if (this._monitor) {
            this._monitor.cancel();
            this._monitor = null;
        }
        this._clear();
        this._unbrand();
        if (this._brandTimer) {
            GLib.source_remove(this._brandTimer);
            this._brandTimer = 0;
        }
        if (this._testTimer) {
            GLib.source_remove(this._testTimer);
            this._testTimer = 0;
        }
    }

    // ---------------------------------------------------------------- logo no botão do menu
    _brandSoon() {
        if (this._brandTimer)
            GLib.source_remove(this._brandTimer);
        let tries = 0;
        this._brandTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1500, () => {
            this._brand();
            tries++;
            if (tries < 8)
                return GLib.SOURCE_CONTINUE; // o painel do Zorin pode ser montado alguns segundos depois
            this._brandTimer = 0;
            return GLib.SOURCE_REMOVE;
        });
    }

    _isZorinLogo(gicon) {
        return gicon instanceof Gio.FileIcon && /zorin-icon-symbolic\.svg$/.test(gicon.get_file().get_path() ?? '');
    }

    _brand() {
        const ours = Gio.FileIcon.new(this.dir.get_child('arasaka-symbolic.svg'));
        const walk = actor => {
            if (actor instanceof St.Icon && !this._branded.has(actor) && this._isZorinLogo(actor.gicon)) {
                const original = actor.gicon;
                actor.gicon = ours;
                // se o menu do Zorin trocar o ícone de novo (configuração mudou), volta o Arasaka
                const id = actor.connect('notify::gicon', () => {
                    if (this._isZorinLogo(actor.gicon))
                        actor.gicon = ours;
                });
                const did = actor.connect('destroy', () => this._branded.delete(actor));
                this._branded.set(actor, {original, ids: [id, did]});
            }
            for (const c of actor.get_children())
                walk(c);
        };
        walk(Main.layoutManager.uiGroup);
    }

    _unbrand() {
        for (const [actor, {original, ids}] of this._branded ?? []) {
            for (const id of ids)
                actor.disconnect(id);
            actor.gicon = original;
        }
        this._branded = new Map();
    }

    _readConfig() {
        try {
            const [, bytes] = GLib.file_get_contents(CONFIG);
            return {...DEFAULTS, ...JSON.parse(new TextDecoder().decode(bytes))};
        } catch {
            return {...DEFAULTS};
        }
    }

    _clear() {
        for (const a of this._bg)
            a.destroy();
        for (const a of this._crt) {
            Main.layoutManager.removeChrome(a);
            a.destroy();
        }
        this._bg = [];
        this._crt = [];
    }

    _rebuild() {
        this._clear();
        for (const m of Main.layoutManager.monitors) {
            if (this._cfg.background) {
                const bg = new BackgroundFx(m);
                Main.layoutManager._backgroundGroup.add_child(bg);
                this._bg.push(bg);
            }
            if (this._cfg.crt) {
                const crt = new CrtFx(m);
                // trackFullscreen: some sozinho quando um jogo ou vídeo está em tela cheia neste monitor
                Main.layoutManager.addChrome(crt, {affectsInputRegion: false, affectsStruts: false, trackFullscreen: true});
                this._crt.push(crt);
            }
        }
    }

    _wantsWindow(actor) {
        if (!this._cfg.windows || !actor || !actor.meta_window)
            return false;
        const t = actor.meta_window.get_window_type();
        return t === Meta.WindowType.NORMAL || t === Meta.WindowType.DIALOG || t === Meta.WindowType.MODAL_DIALOG;
    }

    _onMap(actor) {
        if (this._wantsWindow(actor) && !actor.meta_window.is_fullscreen())
            glitch(actor, {ms: 340, from: 1, to: 0});
    }

    _onDestroy(actor) {
        if (this._wantsWindow(actor))
            glitch(actor, {ms: 220, from: 0.3, to: 1});
    }

    _onOverview() {
        if (this._cfg.overview)
            glitch(Main.layoutManager.overviewGroup, {ms: 300, from: 0.8, to: 0});
    }

    // Teste sem tela (gnome-shell --headless): ARASAKA_FX_SELFTEST=<pasta> tira prints do efeito parado em pontos fixos
    _selfTest() {
        const dir = GLib.getenv('ARASAKA_FX_SELFTEST');
        if (!dir || globalThis._arasakaFxTested)
            return;
        globalThis._arasakaFxTested = true;
        const shot = async name => {
            const file = Gio.File.new_for_path(`${dir}/${name}.png`);
            const stream = file.replace(null, false, Gio.FileCreateFlags.NONE, null);
            await new Shell.Screenshot().screenshot(false, stream);
            stream.close(null);
        };
        const wait = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => r() ?? GLib.SOURCE_REMOVE));
        const log = msg => GLib.file_set_contents(`${dir}/log.txt`, `${msg}\n`);
        this._testTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 3000, () => {
            this._testTimer = 0;
            (async () => {
                try {
                    await shot('1-desktop');
                    // glitch parado no meio, aplicado na tela inteira
                    const fx = new GlitchEffect();
                    fx.amount = 0.7;
                    global.stage.add_effect_with_name('arasaka-test', fx);
                    await new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => r() ?? GLib.SOURCE_REMOVE));
                    await shot('2-glitch');
                    global.stage.remove_effect(fx);
                    Main.overview.show();
                    await new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 120, () => r() ?? GLib.SOURCE_REMOVE));
                    await shot('3-overview');
                    Main.overview.hide();
                    await wait(800);
                    // janela de verdade: print 110 ms depois de aparecer (no meio do glitch de abertura)
                    const mapped = new Promise(r => {
                        const id = global.window_manager.connect('map', () => {
                            global.window_manager.disconnect(id);
                            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 110, () => r() ?? GLib.SOURCE_REMOVE);
                        });
                    });
                    GLib.spawn_command_line_async('gnome-calculator');
                    await mapped;
                    await shot('4-window-open');
                    await wait(900);
                    await shot('5-window');
                    // o mesmo glitch parado na janela (no Shell sem tela a animação passa rápido demais para o print)
                    const win = global.get_window_actors().find(a => a.meta_window.get_window_type() === Meta.WindowType.NORMAL);
                    if (win) {
                        const fx = new GlitchEffect();
                        fx.amount = 0.6;
                        win.add_effect_with_name('arasaka-test', fx);
                        await wait(300);
                        await shot('6-window-glitch');
                        win.remove_effect(fx);
                    }
                    // configuração mudada com a sessão rodando (como o comando arasaka-fx faz)
                    const count = () => `fundo=${Main.layoutManager._backgroundGroup.get_children().filter(a => a instanceof BackgroundFx).length} crt=${Main.uiGroup.get_children().filter(a => a instanceof CrtFx).length}`;
                    const before = count();
                    const brandedBefore = this._branded.size;
                    await shot('7-taskbar');
                    GLib.mkdir_with_parents(GLib.path_get_dirname(CONFIG), 0o700);
                    GLib.file_set_contents(CONFIG, '{"crt": false}');
                    await wait(1500);
                    const afterCfg = count();
                    // bloquear e desbloquear: o GNOME desliga e liga as extensões
                    Main.sessionMode.pushMode('unlock-dialog');
                    await wait(800);
                    const locked = count();
                    Main.sessionMode.popMode('unlock-dialog');
                    await wait(1200);
                    log(`ok | logo no menu: ${brandedBefore} | antes ${before} | config crt=false ${afterCfg} | bloqueado ${locked} | desbloqueado ${count()}`);
                } catch (e) {
                    log(`ERRO ${e}\n${e.stack}`);
                }
            })();
            return GLib.SOURCE_REMOVE;
        });
    }
}
