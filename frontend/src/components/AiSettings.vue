<script setup>
import { computed, onMounted, ref } from 'vue'

import { actions, store } from '@/store'

const chave = ref('')
const salvando = ref(false)
const erro = ref('')
const aberto = ref(false)

const ia = computed(() => store.ia)

const situacao = computed(() => {
  if (!ia.value) return { texto: 'Indisponível', cor: 'neutro' }
  if (!ia.value.sdk_disponivel) return { texto: 'SDK ausente', cor: 'alerta' }
  if (!ia.value.configurada) return { texto: 'Sem chave', cor: 'neutro' }
  return {
    texto: ia.value.origem === 'ambiente' ? 'Chave do ambiente' : 'Chave ativa',
    cor: 'ok',
  }
})

async function salvar() {
  if (!chave.value.trim()) return

  salvando.value = true
  erro.value = ''
  try {
    await actions.salvarChaveDaIA(chave.value.trim())
    // Some do campo assim que sai daqui: nada de segredo parado na tela
    chave.value = ''
  } catch (e) {
    erro.value = e.message
  } finally {
    salvando.value = false
  }
}

async function esquecer() {
  erro.value = ''
  try {
    await actions.esquecerChaveDaIA()
  } catch (e) {
    erro.value = e.message
  }
}

onMounted(() => actions.carregarStatusDaIA())
</script>

<template>
  <section class="ia">
    <button class="cabecalho" :aria-expanded="aberto" @click="aberto = !aberto">
      <span>{{ aberto ? '▾' : '▸' }} Análise por IA</span>
      <span :class="['marca', situacao.cor]">{{ situacao.texto }}</span>
    </button>

    <div v-if="aberto" class="conteudo">
      <p v-if="ia && !ia.sdk_disponivel" class="aviso">
        O pacote do provedor não está instalado nesta imagem. Instale com
        <code>pip install "graphalyzer[ai]"</code>.
      </p>

      <template v-if="ia?.origem !== 'ambiente'">
        <label>
          Chave de API ({{ ia?.modelo || 'claude' }})
          <input
            v-model="chave"
            type="password"
            autocomplete="off"
            spellcheck="false"
            placeholder="cole a chave aqui"
            :disabled="salvando"
            @keyup.enter="salvar"
          />
        </label>

        <div class="acoes">
          <button class="primario" :disabled="!chave.trim() || salvando" @click="salvar">
            {{ salvando ? 'Enviando...' : 'Salvar chave' }}
          </button>
          <button v-if="ia?.origem === 'sessao'" @click="esquecer">Esquecer</button>
        </div>
      </template>

      <p v-else class="aviso ok">
        Chave vinda de variável de ambiente. Para trocar, altere o ambiente.
      </p>

      <p v-if="erro" class="aviso erro">{{ erro }}</p>

      <p class="nota">
        A chave é enviada ao servidor local e fica <strong>só na memória</strong>:
        não vai para disco, log nem para o navegador, e some ao reiniciar. Para
        que ela persista, use a variável de ambiente
        <code>ANTHROPIC_API_KEY</code>.
      </p>

      <p class="nota">
        Com a chave ativa, marque <strong>IA</strong> ao analisar. Ela resume
        cada arquivo e avalia a organização do projeto — o resultado entra na
        documentação exportada.
      </p>
    </div>
  </section>
</template>

<style scoped>
.ia {
  display: grid;
  gap: 0.5rem;
}

.cabecalho {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
}

.cabecalho:hover {
  color: var(--text);
}

.marca {
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.6rem;
  letter-spacing: 0;
  text-transform: none;
  background: var(--surface-alt);
}

.marca.ok {
  background: color-mix(in srgb, #22c55e 22%, transparent);
  color: #15803d;
}

.marca.alerta {
  background: color-mix(in srgb, #f59e0b 25%, transparent);
}

.conteudo {
  display: grid;
  gap: 0.55rem;
}

label {
  display: grid;
  gap: 0.3rem;
  font-size: 0.7rem;
  color: var(--text-muted);
}

input {
  width: 100%;
  padding: 0.45rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  font-size: 0.78rem;
  font-family: ui-monospace, Consolas, monospace;
}

.acoes {
  display: flex;
  gap: 0.4rem;
}

.acoes button {
  flex: 1;
  padding: 0.4rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-alt);
  color: var(--text);
  font-size: 0.73rem;
  cursor: pointer;
}

.acoes .primario {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  font-weight: 600;
}

.acoes button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.aviso {
  margin: 0;
  padding: 0.4rem 0.5rem;
  border-radius: 6px;
  background: color-mix(in srgb, #f59e0b 16%, transparent);
  font-size: 0.7rem;
  line-height: 1.4;
}

.aviso.ok {
  background: color-mix(in srgb, #22c55e 16%, transparent);
}

.aviso.erro {
  background: color-mix(in srgb, #ef4444 18%, transparent);
}

.nota {
  margin: 0;
  font-size: 0.66rem;
  line-height: 1.45;
  color: var(--text-muted);
}

code {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 0.63rem;
}
</style>
