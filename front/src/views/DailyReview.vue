<template>
  <div class="daily-review-page">
    <van-nav-bar title="每日回顾" fixed />
    <div class="review-content">
      <van-loading v-if="loading" class="loading-center" />
      <van-empty v-else-if="reviews.length === 0 && !loading" description="今天没有需要回顾的笔记，太棒了！" />

      <div v-else class="review-list">
        <div class="review-header-bar">
          <span class="review-count">共 {{ reviews.length }} 篇待回顾</span>
          <span class="review-progress">{{ doneCount }} / {{ reviews.length }}</span>
        </div>

        <ReviewCard
          v-for="item in reviews"
          :key="item.note_id"
          :title="item.title"
          :question="getQuestion(item.note_id)"
          :tags="item.tags"
          :category="item.category"
          :review-count="item.review_count"
          :done="doneMap[item.note_id]"
          @click="handleCardClick(item)"
          @review-now="handleCardClick(item)"
          @done="handleDone(item.note_id)"
          @skip="handleSkip(item.note_id)"
        />
      </div>
    </div>

    <!-- 回顾选择题弹窗 -->
    <van-popup
      v-model:show="popupVisible"
      position="bottom"
      round
      :style="{ minHeight: '50vh', padding: '24px 20px', borderRadius: '16px 16px 0 0' }"
      closeable
      @close="resetQuiz"
    >
      <div v-if="quizLoading" class="quiz-loading">
        <van-loading type="spinner" size="24" />
        <p>正在生成至少 5 道回顾问题...</p>
      </div>

      <template v-else-if="quizData">
        <div class="quiz-progress-bar">
          <span>第 {{ currentQuestionIndex + 1 }} / {{ quizQuestions.length }} 题</span>
          <span>{{ answered ? (selectedChoice === quizData.answer ? '答对' : '待巩固') : '请选择答案' }}</span>
        </div>

        <h3 class="quiz-question">{{ quizData.question }}</h3>

        <div class="quiz-choices">
          <div
            v-for="(choice, idx) in quizData.choices"
            :key="idx"
            class="quiz-choice"
            :class="{
              'quiz-choice--correct': answered && choice === quizData.answer,
              'quiz-choice--wrong': answered && selectedChoice === choice && choice !== quizData.answer,
              'quiz-choice--selected': !answered && selectedChoice === choice,
            }"
            @click="selectChoice(choice)"
          >
            <span class="quiz-choice-label">{{ ['A', 'B', 'C', 'D'][idx] }}</span>
            <span class="quiz-choice-text">{{ choice }}</span>
            <span v-if="answered && choice === quizData.answer" class="quiz-choice-icon">✓</span>
            <span v-if="answered && selectedChoice === choice && choice !== quizData.answer" class="quiz-choice-icon">✗</span>
          </div>
        </div>

        <div v-if="answered" class="quiz-result" :class="{ 'quiz-result--correct': selectedChoice === quizData.answer }">
          {{ selectedChoice === quizData.answer ? '回答正确！' : `正确答案是：${quizData.answer}` }}
        </div>

        <div class="quiz-actions">
          <van-button
            v-if="answered"
            type="primary"
            block
            round
            @click="handleQuizDone"
          >
            {{ isLastQuestion ? '标记已回顾' : '下一题' }}
          </van-button>
        </div>
      </template>
    </van-popup>

    <TabBar />
  </div>
</template>

<script setup>
/**
 * DailyReview 每日回顾页面 —— 展示待回顾笔记列表，使用艾宾浩斯曲线算法。
 * 用户滑动浏览卡片，标记已回顾或跳过。
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { showToast } from 'vant'
import { apiConfig } from '../config/api'
import { getAuthHeaders } from '../utils/auth'
import ReviewCard from '../components/ReviewCard.vue'
import TabBar from '../components/TabBar.vue'

const loading = ref(false)
const reviews = ref([])
const questions = reactive({})   /** note_id → 回顾问题（string） */
const doneMap = reactive({})     /** note_id → 是否已完成 */
const doneCount = ref(0)

/** 弹窗状态 */
const popupVisible = ref(false)
const quizLoading = ref(false)
const quizQuestions = ref([])      /** Array<{ question, choices, answer }> */
const quizData = computed(() => quizQuestions.value[currentQuestionIndex.value] || null)
const currentQuestionIndex = ref(0)
const currentNoteId = ref('')
const selectedChoice = ref('')
const answered = ref(false)
const isLastQuestion = computed(() => currentQuestionIndex.value >= quizQuestions.value.length - 1)

/** 请求头 */
function getHeaders() {
  return getAuthHeaders({ 'Content-Type': 'application/json' })
}

/** 获取某个笔记的回顾问题（带缓存） */
function getQuestion(noteId) {
  return questions[noteId] || '点击立即回顾，生成知识点选择题'
}

function normalizeQuizQuestion(question) {
  if (!question?.question || !Array.isArray(question.choices) || question.choices.length === 0) {
    return null
  }

  const normalized = { ...question, answer: String(question.answer || '') }
  const letterIndex = ['A', 'B', 'C', 'D'].indexOf(normalized.answer.toUpperCase())
  if (letterIndex >= 0 && normalized.choices[letterIndex]) {
    normalized.answer = normalized.choices[letterIndex]
  }
  return normalized
}

function normalizeQuizQuestions(data) {
  const rawQuestions = Array.isArray(data?.questions) ? data.questions : [data]
  return rawQuestions.map(normalizeQuizQuestion).filter(Boolean)
}

/** 点击卡片 —— 弹窗展示选择题 */
async function handleCardClick(item) {
  if (doneMap[item.note_id]) return
  currentNoteId.value = item.note_id
  popupVisible.value = true
  quizLoading.value = true
  quizQuestions.value = []
  currentQuestionIndex.value = 0
  selectedChoice.value = ''
  answered.value = false

  try {
    const res = await fetch(apiConfig.endpoints.reviewQuestion(item.note_id), {
      headers: getHeaders(),
    })
    const json = await res.json()
    if (json.code === 200 && json.data) {
      const normalizedQuestions = normalizeQuizQuestions(json.data)
      if (normalizedQuestions.length === 0) {
        showToast('回顾问题为空')
        popupVisible.value = false
        return
      }
      quizQuestions.value = normalizedQuestions
      // 缓存问题文本供卡片展示
      questions[item.note_id] = `共 ${normalizedQuestions.length} 道知识点选择题，点击开始回顾`
    } else {
      showToast('获取回顾问题失败')
      popupVisible.value = false
    }
  } catch (e) {
    showToast('网络错误')
    popupVisible.value = false
  } finally {
    quizLoading.value = false
  }
}

/** 选择选项 */
function selectChoice(choice) {
  if (answered.value) return
  selectedChoice.value = choice
  answered.value = true
}

/** 答完后标记已回顾 */
async function handleQuizDone() {
  if (!answered.value) return

  if (!isLastQuestion.value) {
    currentQuestionIndex.value++
    selectedChoice.value = ''
    answered.value = false
    return
  }

  const noteId = currentNoteId.value
  try {
    const res = await fetch(apiConfig.endpoints.reviewDone(noteId), {
      method: 'POST',
      headers: getHeaders(),
    })
    const json = await res.json()
    if (json.code === 200) {
      doneMap[noteId] = true
      doneCount.value++
      popupVisible.value = false
      showToast('已标记回顾')
    }
  } catch (e) {
    showToast('操作失败')
  }
}

/** 重置弹窗状态 */
function resetQuiz() {
  quizQuestions.value = []
  currentQuestionIndex.value = 0
  selectedChoice.value = ''
  answered.value = false
  quizLoading.value = false
}

/** 加载今日回顾列表 */
async function loadReviews() {
  loading.value = true
  try {
    const res = await fetch(apiConfig.endpoints.reviewToday, { headers: getHeaders() })
    const json = await res.json()
    if (json.code === 200) {
      reviews.value = json.data.reviews || []
    }
  } catch (e) {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

/** 标记已回顾（卡片按钮） */
async function handleDone(noteId) {
  try {
    const res = await fetch(apiConfig.endpoints.reviewDone(noteId), {
      method: 'POST',
      headers: getHeaders(),
    })
    const json = await res.json()
    if (json.code === 200) {
      doneMap[noteId] = true
      doneCount.value++
      showToast('已标记回顾')
    }
  } catch (e) {
    showToast('操作失败')
  }
}

/** 跳过 */
function handleSkip(noteId) {
  doneMap[noteId] = true
  doneCount.value++
}

onMounted(() => {
  loadReviews()
})
</script>

<style scoped>
.daily-review-page {
  min-height: 100vh;
  background: var(--van-background, #f7f8fa);
}
.review-content {
  padding-top: 48px;
  padding-bottom: 60px;
}
.loading-center {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}
.review-list {
  padding: 16px;
}
.review-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.review-count {
  font-size: 14px;
  color: #666;
}
.review-progress {
  font-size: 14px;
  color: var(--van-primary-color, #D4914A);
  font-weight: 600;
}

/* 选择题弹窗 */
.quiz-loading {
  text-align: center;
  padding: 60px 0;
  color: #999;
}
.quiz-loading p {
  margin-top: 12px;
  font-size: 14px;
}
.quiz-progress-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  color: var(--van-primary-color, #D4914A);
  font-size: 13px;
  font-weight: 600;
}
.quiz-question {
  margin: 0 0 24px;
  font-size: 17px;
  font-weight: 600;
  color: #333;
  line-height: 1.6;
}
.quiz-choices {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.quiz-choice {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1.5px solid #e8e8e8;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}
.quiz-choice:active {
  transform: scale(0.98);
}
.quiz-choice--selected {
  border-color: var(--van-primary-color, #D4914A);
  background: rgba(212, 145, 74, 0.06);
}
.quiz-choice--correct {
  border-color: #07c160;
  background: rgba(7, 193, 96, 0.08);
}
.quiz-choice--wrong {
  border-color: #ee0a24;
  background: rgba(238, 10, 36, 0.06);
}
.quiz-choice-label {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #f5f5f5;
  font-size: 13px;
  font-weight: 600;
  color: #666;
  flex-shrink: 0;
}
.quiz-choice--correct .quiz-choice-label {
  background: #07c160;
  color: #fff;
}
.quiz-choice--wrong .quiz-choice-label {
  background: #ee0a24;
  color: #fff;
}
.quiz-choice-text {
  flex: 1;
  font-size: 15px;
  color: #333;
}
.quiz-choice-icon {
  font-size: 18px;
  font-weight: 700;
}
.quiz-choice--correct .quiz-choice-icon {
  color: #07c160;
}
.quiz-choice--wrong .quiz-choice-icon {
  color: #ee0a24;
}
.quiz-result {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  background: rgba(238, 10, 36, 0.08);
  color: #ee0a24;
}
.quiz-result--correct {
  background: rgba(7, 193, 96, 0.08);
  color: #07c160;
}
.quiz-actions {
  margin-top: 20px;
}
</style>
