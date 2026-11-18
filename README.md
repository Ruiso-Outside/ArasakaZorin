# ARASAKA // Tema completo para Zorin OS

Tema Cyberpunk 2077 / Arasaka para **Zorin OS 17 e 18** (Core/Pro, GNOME), do boot ao terminal.
Uso pessoal: o logo e o nome Arasaka pertencem à CD PROJEKT RED, e a fonte `cedge1` usa a licença
FontStruct Non-Commercial.

## O que muda

| Etapa | O que você vê |
|---|---|
| **GRUB** | Menu de boot preto com logo Arasaka, painel HUD com cantos cortados, item selecionado em vermelho e contagem regressiva |
| **Plymouth** | Logo com fade-in e pulso, glitch aleatório, barra de progresso com mensagens ("LOADING NEURAL KERNEL…"), feixe de varredura. Também cobre a tela de senha de disco criptografado e o desligamento |
| **Login (GDM)** | Fundo "Secure Access Terminal", logo Arasaka, campo de senha estilo terminal, cursor e fonte do tema |
| **Desktop** | Tema GTK3/GTK4/libadwaita preto e vermelho com cantos retos, painel e menus do GNOME Shell, Alt+Tab, notificações e OSD |
| **Ícones** | Pastas vermelhas (Papirus), logo Arasaka no menu iniciar e ícone de terminal próprio |
| **Cursores** | 20 cursores próprios (com animação de "carregando") e mais de 80 apelidos |
| **Sons** | Sons sintetizados: entrada/saída da sessão, notificações, erros, USB, captura de tela |
| **Wallpapers** | 5 fundos em 2560×1440: Core, Crimson, Glitch, HUD e Secure Access |
| **Terminal** | Perfil "Arasaka" no GNOME Terminal, prompt `┌─[user@host]─[~]` com branch do git e banner com o logo em ASCII e dados do sistema |
| **Fontes** | cedge1 (títulos), Rajdhani (interface) e Share Tech Mono (terminal), as duas últimas baixadas do Google Fonts |

## Instalar

1. Copie a pasta `ArasakaZorin` (ou o `ArasakaZorin.tar.gz`) para o Zorin.
2. No terminal, dentro da pasta:

```bash
tar xzf ArasakaZorin.tar.gz && cd ArasakaZorin
```

```bash
./install.sh
```

3. Rode **sem sudo**. Ele pede a senha quando precisa.
4. Reinicie o computador para ver tudo, do GRUB até o desktop.

### Opções

| Opção | Efeito |
|---|---|
| `--sem-grub` | Não mexe no GRUB |
| `--sem-plymouth` | Não troca a tela de carregamento |
| `--sem-login` | Não mexe na tela de login |
| `--sem-terminal` | Não mexe no bash nem no perfil do terminal |
| `--sem-sons` | Não troca os sons |
| `--sem-download` | Não baixa fontes (funciona offline, mas usa as fontes padrão) |
| `--grub-oculto` | Mantém o menu do GRUB escondido (o Zorin esconde por padrão; o tema mostra o menu por 5 s) |
| `-y` | Não pede confirmação |

## Desinstalar

```bash
./uninstall.sh
```

Restaura as configurações antigas, o GRUB, o Plymouth e a tela de login a partir dos backups em
`/var/lib/arasaka-theme` e `~/.config/arasaka`.

## Dicas

- Para mostrar o banner de novo no terminal, rode `arasaka`.
- Para desligar o banner, coloque `export ARASAKA_BANNER=0` no `~/.bashrc`, antes do bloco do Arasaka.
- Para trocar o wallpaper, vá em Configurações > Fundo, onde aparecem os 5 fundos Arasaka.
- Se você mudar o tema pelo app **Aparência do Zorin**, ele sobrescreve o Arasaka. Para voltar, rode `./install.sh` de novo.
- Os apps Flatpak com libadwaita também ficam tematizados. Apps GTK3 em Flatpak mantêm o tema padrão.

## Regenerar as imagens (opcional)

Todas as imagens, cursores, sons e o logo ASCII são gerados por `build/build_assets.py`, que só
precisa do Pillow:

```bash
python3 build/build_assets.py
```

Para mudar textos, cores ou a posição dos elementos, edite o script e rode de novo.

## Estrutura

```
install.sh / uninstall.sh
build/build_assets.py         gerador de assets
theme/
  backgrounds/                wallpapers + XML para Configurações > Fundo
  grub/arasaka/               tema do GRUB (theme.txt gerado na instalação)
  plymouth/arasaka/           tema script do Plymouth
  gtk/Arasaka/                overrides GTK3, GTK4 e libadwaita
  shell/arasaka-shell.css     GNOME Shell + tela de login
  icons/ cursors/ sounds/     ícones, cursores Xcursor, sons
  terminal/                   prompt, banner, logo ASCII, paleta do Ptyxis
  fonts/cedge1.ttf
```
