# Direção visual do painel

Remodelação do painel web no estilo de vidro da Apple (visionOS). Este documento guia a implementação; os mockups mostram cada tela.

## Princípios

- **Vidro sobre um ambiente desfocado:** painéis translúcidos flutuam sobre um fundo escuro com formas fora de foco.
- **Um só elemento vivo por tela:** a esfera do Alfred. O resto é quieto.
- **Neutro:** fundo grafite, sem amarelo e sem azul. A cor vem só dos estados e das fotos das sessões.
- **Pílulas e círculos:** botões de ícone redondos, controles em pílula, cantos bem arredondados.
- **Pouca informação por vez:** listas agrupadas como nos Ajustes do iPhone; detalhe só no cartão aberto.

## Referências

- **Esfera:** [Strands](https://reactbits.dev/animations/strands), do React Bits (MIT + Commons Clause: pode usar no app, não pode revender o componente). WebGL2 puro, sem dependência; tem as props `listening` e `level` para a voz.
- **Material, listas e controles:** visionOS e os Ajustes do iOS.
- **Uso do plano:** anéis como os do Apple Watch.
- **Taste Skill:** um único elemento animado por tela.

## Cores

| Token | Valor | Uso |
|---|---|---|
| `--page` | `#0a0a0c` | fundo da página |
| fundo do ambiente | degradê `#19191c` → `#09090b`, formas `#3c3c42`, `#8a8a94`, `#2a2a30`, `#303036` com blur 60px | atrás dos painéis |
| `--ink` | `#f5f5f7` | texto principal |
| `--ink-2` | `rgba(235,235,245,.62)` | texto secundário |
| `--ink-3` | `rgba(235,235,245,.36)` | dicas, placeholders |
| `--fill` / `--fill-on` | `rgba(255,255,255,.10)` / `.22` | fundo de controle / selecionado |
| `--blue` | `#0a84ff` | links, foco, falando |
| `--teal` | `#64d2ff` | sessão trabalhando |
| `--orange` | `#ff9f0a` | aguarda você, contexto acima de 60% |
| `--green` | `#30d158` | ligado, feito |
| vermelho | `#ff453a` | apagar, contexto acima de 80% |

## Material de vidro

```css
.glass {
  background: linear-gradient(180deg, rgba(255,255,255,.16), rgba(255,255,255,.05)), rgba(118,118,128,.24);
  backdrop-filter: blur(40px) saturate(170%);
  border: 1px solid rgba(255,255,255,.14);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.22), 0 24px 60px rgba(0,0,0,.35);
}
```

- Listas e campos dentro do vidro: `rgba(0,0,0,.16–.2)`.
- Raios: painel 30px, cartão 24px, linha de lista 14–16px, controles em pílula (999px).

## Tipografia

- Fonte do sistema da Apple quando houver; senão Inter (`-apple-system, 'SF Pro Text', 'Inter', system-ui`).
- Títulos de página: 22–28px, peso 700, `letter-spacing: -.02em`.
- Corpo: 13–14px, peso 500 nos nomes.
- Rótulos de seção: 13px, caixa-alta, peso 600, `--ink-2`.
- Números alinhados com `tabular-nums`.

## Esfera do Alfred

- Strands com vidro, paleta espectral padrão, centro da tela Painel.
- Estados da voz (`useVoice`):

| Estado | `listening` | `level` | `speed` | `energy` |
|---|---|---|---|---|
| Em espera | não | 0 | 0.5 | 0.4 |
| Ouvindo | sim | nível do microfone | 1 | 0.8 |
| Pensando | não | 0.3 | 1.8 | 0.6 |
| Falando | sim | nível da fala | 1.1 | 0.9 |

- **Sem WebGL2** (visualizador do app desktop, algumas VMs): esfera em CSS com faixas coloridas desfocadas, mesma paleta. O Strands não mostra nada sozinho quando falta WebGL, então o fallback é obrigatório.
- Sai do painel: `three`, `@react-three/fiber` e o orb atual.

## Componentes

- **Barra de navegação:** pílula vertical à esquerda com ícones redondos (Painel, Projetos, Configurações).
- **Barra de controle (ornamento):** pílula na base com microfone, estado e medidor, seletor de modelo, nova conversa e transcrição.
- **Balão de fala:** pílula com o avatar do Alfred e a última frase dele.
- **Lista agrupada:** linhas com ícone quadrado colorido (raio 8px), nome, detalhe e valor à direita, separadas por linha fina.
- **Controle segmentado, chave liga/desliga (verde), popup de valor e stepper** no padrão do iOS.
- **Anel de estado na foto da sessão:** azul girando quando trabalha; laranja com bolinha quando aguarda você.

## Telas

- **Painel (layout Janela):** navegação | lista de sessões | esfera, balão e barra de controle | cartão da sessão ou transcrição.
- **Cartão da sessão** (no estilo do "Tocando agora"): foto grande, nome, projeto e branch, estado, tarefa com progresso, pedido de permissão com Negar e Permitir, contexto, modelo, subagentes, e ações (limpar, falar com, apagar).
- **Projetos:** cartões como álbuns; a capa junta a inicial do projeto e as fotos das sessões, com selo de quem trabalha ou espera. Mostra a descrição, os apelidos e as contagens. O último cartão é "Novo projeto".
- **Projeto:** painel lateral com marca, nome, descrição, nomes falados e "Apagar projeto". Painel principal com ambientes (descrição e sessões em cada um, worktree recuado) e sessões do projeto.
- **Configurações:** barra lateral como nos Ajustes, com Uso e limites (anéis e gasto por sessão), Modelos, Sessões abertas e MCPs (chaves e "Desligar/Ligar todos").

## Movimento

- Só a esfera, o anel de quem trabalha e os medidores se movem.
- Transições de 200ms; cartões crescem 2% no hover.
- `prefers-reduced-motion` desliga as animações.

## Mockups

- [Painel, layouts Janela e Ornamentos](https://claude.ai/artifact/9v7ZF6iShWm7TTdPC7hWcE)
- [Sessões, com as três opções de foto](https://claude.ai/artifact/VZXzh69Zen2HUiJtNBvyEs)
- [Projetos, Projeto e Configurações](https://claude.ai/artifact/TRisX7cDuLVeakNfrFvKVL)

## Decisões

- **Foto das sessões:** retrato 3D. Enquanto o retrato não existe, a sessão mostra o monograma (iniciais num degradê estável pelo nome). Geração: [ADR 0009](adr/0009-session-portraits-via-mcp.md).
- **Bonecos do mapa:** saíram, junto com a opção "Tamanho dos agentes no mapa" (`figure_scale`).
- **Permissões:** o cartão não tem Negar/Permitir; a confirmação continua por voz, como manda a SPEC.
