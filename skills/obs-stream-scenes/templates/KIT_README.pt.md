# {{NAME}}: kit do OBS

Gerado pela skill **obs-stream-scenes**. Pra mudar cores, textos fixos, cenas ou layout, edite
`studio.json` e peça pra sua IA reconstruir o kit (ou rode `python "{{SCRIPTS}}/build_kit.py" "{{KIT}}"`).
Não edite os arquivos de `overlays/` na mão: a próxima montagem sobrescreve.

## Cenas e atalhos

| Cena | Atalho |
| ---- | ------ |
{{SCENES}}

Gravar e parar: `{{HK_RECORD}}` · Live e parar: `{{HK_STREAM}}`. Os atalhos do OBS funcionam mesmo com
outro programa em primeiro plano.

## Textos que mudam a cada aula ou live

Edite estes arquivos no Bloco de Notas e salve. O OBS mostra a mudança em uns 2 segundos, sem
reiniciar nada. Use uma linha só em cada arquivo.

{{TEXTS}}

## Antes de gravar ou entrar ao vivo

1. Ative o **Não incomodar** do sistema, pra não aparecer notificação na tela.
2. Em telas de navegador, use **zoom de 125% a 150%**: a tela entra reduzida na moldura e o zoom
   mantém os textos legíveis no vídeo.
3. Se for gravar a câmera separada também (celular, câmera DSLR), **bata uma palma** no começo: ela
   vira o ponto de sincronia na edição.
4. Confira a cena inicial e grave (ou entre ao vivo).

As gravações vão para `{{RECORDINGS}}`.

## Se a pasta do kit mudar de lugar

O OBS aponta pros arquivos por caminho absoluto. Se mover esta pasta, rode a montagem de novo
(`build_kit.py` e `configure_obs.py`) pra ele achar os arquivos no lugar novo.
