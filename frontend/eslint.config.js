import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'
import tsParser from '@typescript-eslint/parser'

// Bassira/MiroShark — Vue 3, PAS de TypeScript (CLAUDE.md).
// Périmètre : catch de vraies erreurs (variables non définies, imports morts,
// mauvais usage Vue) — pas de règles de style cosmétique qui forceraient un
// reformat massif de ~60 composants existants. US-212.
export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      // 6 SFC historiques utilisent <script setup lang="ts"> malgré la stack
      // JS déclarée (CLAUDE.md) — parser seulement (pas de règles type-aware,
      // pas de tsconfig) pour que ESLint les lise sans forcer une migration.
      parserOptions: {
        parser: tsParser,
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      'no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
      }],
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'off',
      'vue/require-default-prop': 'off',
      'vue/attributes-order': 'off',
      'vue/html-self-closing': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-indent': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/first-attribute-linebreak': 'off',
    },
  },
  {
    // Les 6 SFC en lang="ts" référencent des types DOM ambients (RequestInit,
    // etc.) que no-undef ne peut pas résoudre sans le plugin type-aware
    // complet (hors périmètre US-212) — TypeScript lui-même vérifie déjà ces
    // positions de type. Convention officielle typescript-eslint : no-undef
    // désactivé sur les fichiers TS.
    files: [
      'src/components/AdminReportTree.vue',
      'src/components/RawMdEditor.vue',
      'src/components/TiptapEditor.vue',
      'src/components/VersionDiff.vue',
      'src/views/AdminReportReviewView.vue',
      'src/views/AdminReportTrackingView.vue',
    ],
    rules: {
      'no-undef': 'off',
    },
  },
  {
    ignores: ['dist/**', 'node_modules/**', 'playwright-report/**', 'test-results/**'],
  },
]
