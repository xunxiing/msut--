# 教程AI搜索+问答系统设计方案

## 1. 需求重新理解

根据你的最新反馈，你需要的是一个**结合AI问答和传统搜索**的系统：
- **搜索功能**: 用户可以通过关键词搜索找到相关教程
- **AI问答**: 用户可以通过自然语言提问，AI基于教程内容给出答案
- **统一界面**: 一个输入框支持两种模式，或者可以切换模式

## 2. 系统架构设计

### 2.1 双模式架构
```
┌─────────────────────────────────────────────────────────┐
│                   统一输入界面                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │  [搜索/提问...]                    [🔍/💬]切换 │  │
│  └───────────────────────────────────────────────────┘  │
│           │                                │             │
│           ▼                                ▼             │
│  ┌─────────────────┐              ┌─────────────────┐    │
│  │   传统搜索模式    │              │   AI问答模式     │    │
│  │                 │              │                 │    │
│  │ • 关键词匹配     │              │ • 自然语言理解   │    │
│  │ • 相关性排序     │              │ • 语义检索       │    │
│  │ • 快速返回结果   │              │ • 答案生成       │    │
│  └─────────────────┘              └─────────────────┘    │
│           │                                │             │
│           └──────────┬──────────────────────┘             │
│                      ▼                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              MiniRAG双引擎系统                       │  │
│  │  ┌──────────────┐        ┌──────────────┐         │  │
│  │  │  搜索索引引擎 │        │  问答RAG引擎  │         │  │
│  │  │              │        │              │         │  │
│  │  │ • 倒排索引    │        │ • 向量索引    │         │  │
│  │  │ • 关键词检索  │        │ • 语义检索    │         │  │
│  │  │ • 相关性评分  │        │ • 上下文生成  │         │  │
│  │  └──────────────┘        └──────────────┘         │  │
│  └─────────────────────────────────────────────────────┘  │
│                      │                                   │
│           ┌──────────┴──────────┐                        │
│           ▼                     ▼                        │
│  ┌─────────────────┐   ┌─────────────────┐              │
│  │   搜索结果展示    │   │   问答对话展示   │              │
│  │                 │   │                 │              │
│  │ • 教程列表       │   │ • 对话式交互     │              │
│  │ • 相关片段       │   │ • 详细答案       │              │
│  │ • 快速访问       │   │ • 引用来源       │              │
│  └─────────────────┘   └─────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

### 2.2 技术实现
- **统一入口**: 一个输入框，支持模式切换或智能识别
- **双引擎**: 传统搜索索引 + RAG问答引擎
- **手动路由**: 用户手动选择最佳模式
- **独立结果**: 分别展示两种结果

## 3. 数据库设计

### 3.1 核心数据表
```sql
-- 教程内容表
CREATE TABLE tutorial_contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content_text TEXT NOT NULL,        -- 提取的纯文本内容
    content_chunks TEXT,               -- JSON格式，分块信息
    file_info TEXT,                    -- JSON格式，文件元数据
    search_indexed BOOLEAN DEFAULT FALSE,
    rag_indexed BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
);

-- 搜索记录表
CREATE TABLE search_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    query_type TEXT NOT NULL,          -- 'search' 或 'qa'
    user_id INTEGER,
    results_count INTEGER DEFAULT 0,
    response_time REAL,                -- 响应时间(秒)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 问答会话表
CREATE TABLE qa_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,          -- 会话标识
    user_id INTEGER,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sources TEXT,                      -- JSON格式，引用来源
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 教程访问统计
CREATE TABLE tutorial_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL,
    search_count INTEGER DEFAULT 0,
    qa_count INTEGER DEFAULT 0,
    last_accessed TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
);
```

### 3.2 索引优化
```sql
-- 搜索优化
CREATE INDEX idx_tutorial_contents_search ON tutorial_contents(search_indexed);
CREATE INDEX idx_tutorial_contents_rag ON tutorial_contents(rag_indexed);
CREATE INDEX idx_search_records_query ON search_records(query);
CREATE INDEX idx_search_records_type ON search_records(query_type);

-- 全文搜索虚拟表
CREATE VIRTUAL TABLE tutorial_fts USING fts5(
    title, 
    content_text,
    content='tutorial_contents',
    content_rowid='id'
);
```

## 4. 双模式API设计

### 4.1 统一搜索/问答API
```typescript
// 统一搜索接口
POST /api/tutorials/search-and-ask
{
    query: string;              // 用户输入
    mode: 'search' | 'qa';      // 模式，用户手动选择
    limit?: number;             // 返回结果数量
    context?: {                  // 问答模式下的上下文
        session_id?: string;
        previous_qa?: Array<{q: string, a: string}>;
    };
}

// 返回格式
{
    query_type: 'search' | 'qa';        // 实际使用的模式
    query_processed: string;            // 处理后的查询
    
    // 搜索结果（如果是搜索模式）
    search_results?: {
        total: number;
        results: Array<{
            resource_id: number;
            title: string;
            excerpt: string;
            relevance_score: number;
            file_type: string;
            resource_slug: string;
            share_url: string;
        }>;
        search_time: number;
    };
    
    // 问答结果（如果是问答模式）
    qa_result?: {
        answer: string;
        confidence: number;
        sources: Array<{
            resource_id: number;
            title: string;
            excerpt: string;
            relevance_score: number;
        }>;
        session_id: string;
        answer_time: number;
    };
    
    // 建议（可选）
    suggestions?: {
        related_queries: string[];
    };
}

// 获取搜索建议
GET /api/tutorials/suggestions?query=关键词
// 返回
{
    suggestions: string[];
    popular_queries: string[];
    auto_complete: string[];
}

// 获取历史记录
GET /api/tutorials/history
// 返回
{
    recent_searches: Array<{
        query: string;
        type: 'search' | 'qa';
        timestamp: string;
    }>;
    qa_sessions: Array<{
        session_id: string;
        last_question: string;
        timestamp: string;
    }>;
}
```

### 4.2 模式选择
用户通过界面手动选择搜索或问答模式，系统不再自动判断查询模式。

## 5. MiniRAG双引擎配置

### 5.1 搜索引擎配置
```python
# 传统搜索配置
SEARCH_ENGINE_CONFIG = {
    "type": "traditional",
    "indexing": {
        "method": "inverted_index",
        "tokenizer": "jieba",           # 中文分词
        "stop_words": ["的", "了", "在", "是", "我"],  # 停用词
        "synonyms": {                    # 同义词
            "模组": ["mod", "模块"],
            "安装": ["setup", "配置"]
        }
    },
    "ranking": {
        "algorithm": "bm25",
        "field_weights": {
            "title": 2.0,               # 标题权重更高
            "content": 1.0
        }
    }
}
```

### 5.2 问答引擎配置
```python
# RAG问答配置
QA_ENGINE_CONFIG = {
    "vector_store": {
        "type": "faiss",
        "dimension": 384,
        "index_type": "IndexFlatIP"
    },
    "embedding": {
        "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "device": "cpu"
    },
    "llm": {
        "type": "openai",              # 或其他LLM
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 500,
        "system_prompt": "你是一个甜瓜游乐场教程助手，基于提供的教程内容回答问题。回答要简洁明了，步骤清晰。"
    },
    "retrieval": {
        "top_k": 5,                    # 检索top5相关片段
        "min_score": 0.7,              # 最小相关性阈值
        "rerank": True                 # 是否重排序
    },
    "generation": {
        "include_sources": True,       # 包含引用来源
        "answer_template": "基于教程内容：{context}\n\n回答：{answer}\n\n相关教程：{sources}"
    }
}
```

## 6. 前端界面设计

### 6.1 统一搜索界面
```vue
<!-- TutorialSearch.vue -->
<template>
  <div class="tutorial-search-container">
    <!-- 搜索输入区域 -->
    <div class="search-input-section">
      <div class="search-box">
        <el-input
          v-model="query"
          :placeholder="currentMode === 'search' ? '搜索教程...' : '提问关于教程的问题...'"
          size="large"
          @keyup.enter="handleSearch"
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #suffix>
            <el-button-group>
              <el-button
                :type="currentMode === 'search' ? 'primary' : 'default'"
                @click="switchMode('search')"
                size="small"
              >
                <el-icon><Document /></el-icon> 搜索
              </el-button>
              <el-button
                :type="currentMode === 'qa' ? 'primary' : 'default'"
                @click="switchMode('qa')"
                size="small"
              >
                <el-icon><ChatDotRound /></el-icon> 问答
              </el-button>
            </el-button-group>
          </template>
        </el-input>
        <el-button
          type="primary"
          size="large"
          @click="handleSearch"
          :loading="loading"
        >
          {{ currentMode === 'search' ? '搜索' : '提问' }}
        </el-button>
      </div>
      
      <!-- 搜索建议 -->
      <div v-if="suggestions.length > 0" class="search-suggestions">
        <span>建议：</span>
        <el-tag
          v-for="suggestion in suggestions"
          :key="suggestion"
          @click="query = suggestion"
          class="suggestion-tag"
        >
          {{ suggestion }}
        </el-tag>
      </div>
    </div>

    <!-- 结果展示区域 -->
    <div class="results-section" v-if="hasResults">
      <!-- 搜索结果 -->
      <div v-if="result.search_results" class="search-results">
        <div class="results-header">
          找到 {{ result.search_results.total }} 个相关教程
          <span class="search-time">({{ result.search_results.search_time }}秒)</span>
        </div>
        
        <div v-for="item in result.search_results.results" :key="item.resource_id" class="result-card">
          <h3 @click="goToTutorial(item.share_url)" class="result-title">
            <el-icon><Document /></el-icon>
            {{ item.title }}
          </h3>
          <div class="result-meta">
            <el-tag size="small">{{ item.file_type }}</el-tag>
            <span class="relevance-score">相关度: {{ (item.relevance_score * 100).toFixed(1) }}%</span>
          </div>
          <p class="result-excerpt" v-html="highlightKeywords(item.excerpt)"></p>
          <el-button @click="goToTutorial(item.share_url)" text type="primary">
            查看详细教程 →
          </el-button>
        </div>
      </div>

      <!-- 问答结果 -->
      <div v-if="result.qa_result" class="qa-results">
        <div class="qa-header">
          <el-icon><ChatDotRound /></el-icon>
          智能回答
          <span class="confidence">置信度: {{ (result.qa_result.confidence * 100).toFixed(1) }}%</span>
        </div>
        
        <div class="qa-answer">
          <div class="answer-content" v-html="formatAnswer(result.qa_result.answer)"></div>
          
          <div v-if="result.qa_result.sources.length > 0" class="qa-sources">
            <h4>参考教程：</h4>
            <div v-for="source in result.qa_result.sources" :key="source.resource_id" class="source-item">
              <el-link @click="goToTutorial(source.resource_slug)" :underline="false">
                <el-icon><Document /></el-icon>
                {{ source.title }}
              </el-link>
              <span class="source-relevance">相关度: {{ (source.relevance_score * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>

        <!-- 继续对话 -->
        <div class="qa-continue">
          <el-input
            v-model="followUpQuestion"
            placeholder="继续提问..."
            size="small"
            @keyup.enter="continueQA"
          >
            <template #suffix>
              <el-button @click="continueQA" :loading="qaLoading" size="small">
                发送
              </el-button>
            </template>
          </el-input>
        </div>
      </div>

      <!-- 相关查询建议 -->
      <div v-if="result.suggestions?.related_queries.length > 0" class="related-queries">
        <h4>相关搜索：</h4>
        <el-tag
          v-for="related in result.suggestions.related_queries"
          :key="related"
          @click="query = related; handleSearch()"
          class="related-tag"
        >
          {{ related }}
        </el-tag>
      </div>
    </div>

    <!-- 空状态和加载状态 -->
    <div v-else class="empty-state">
      <div v-if="loading" class="loading-state">
        <el-icon class="is-loading"><Loading /></el-icon>
        <p>{{ currentMode === 'search' ? '正在搜索教程...' : 'AI正在思考...' }}</p>
      </div>
      
      <div v-else-if="!hasSearched" class="welcome-state">
        <el-icon size="48"><Search /></el-icon>
        <h3>甜瓜游乐场教程搜索</h3>
        <p>输入关键词搜索教程，或切换到问答模式向AI提问</p>
        
        <div class="quick-actions">
          <h4>热门搜索：</h4>
          <el-tag
            v-for="popular in popularSearches"
            :key="popular"
            @click="query = popular; handleSearch()"
            class="popular-tag"
          >
            {{ popular }}
          </el-tag>
        </div>
      </div>
      
      <div v-else class="no-results">
        <el-icon size="48"><DocumentDelete /></el-icon>
        <h3>未找到相关结果</h3>
        <p>试试其他关键词</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { 
  Search, Document, ChatDotRound, Loading, DocumentDelete 
} from '@element-plus/icons-vue'

// 状态管理
const query = ref('')
const currentMode = ref<'search' | 'qa'>('search')
const loading = ref(false)
const qaLoading = ref(false)
const hasSearched = ref(false)
const hasResults = computed(() => {
  return !!(result.value.search_results?.results.length || result.value.qa_result)
})

const result = ref({
  query_type: 'search',
  search_results: null,
  qa_result: null,
  suggestions: null
})

const suggestions = ref<string[]>([])
const followUpQuestion = ref('')
const popularSearches = ref(['安装教程', '模组使用', '游戏配置', '常见问题'])

// 搜索建议
const generateSuggestions = () => {
  if (!query.value) return
  
  // 基于输入生成建议
  const input = query.value.toLowerCase()
  const allSuggestions = [
    '安装教程', '模组安装教程', '游戏安装步骤',
    '模组使用教程', '模组配置教程', '模组管理',
    '游戏设置教程', '游戏配置指南', '性能优化',
    '常见问题', '错误解决', '故障排除'
  ]
  
  suggestions.value = allSuggestions.filter(s => 
    s.toLowerCase().includes(input) && s !== input
  ).slice(0, 5)
}

// 搜索处理
const handleSearch = async () => {
  if (!query.value.trim()) return
  
  loading.value = true
  hasSearched.value = true
  
  try {
    const response = await fetch('/api/tutorials/search-and-ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query.value,
        mode: currentMode.value,
        limit: 10
      })
    })
    
    result.value = await response.json()
    generateSuggestions()
    
  } catch (error) {
    console.error('搜索失败:', error)
  } finally {
    loading.value = false
  }
}

// 模式切换
const switchMode = (mode: 'search' | 'qa') => {
  currentMode.value = mode
  // 清除之前的结果，让用户重新输入查询
  result.value = {
    query_type: mode,
    search_results: null,
    qa_result: null,
    suggestions: null
  }
}

// 继续问答
const continueQA = async () => {
  if (!followUpQuestion.value.trim() || !result.value.qa_result) return
  
  qaLoading.value = true
  try {
    const response = await fetch('/api/tutorials/continue-qa', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: result.value.qa_result.session_id,
        question: followUpQuestion.value
      })
    })
    
    const newResult = await response.json()
    // 更新问答结果
    result.value.qa_result = newResult.qa_result
    followUpQuestion.value = ''
    
  } catch (error) {
    console.error('继续问答失败:', error)
  } finally {
    qaLoading.value = false
  }
}

// 工具函数
const highlightKeywords = (text: string) => {
  if (!query.value) return text
  const keywords = query.value.split(' ')
  let highlighted = text
  keywords.forEach(keyword => {
    if (keyword.trim()) {
      const regex = new RegExp(`(${keyword})`, 'gi')
      highlighted = highlighted.replace(regex, '<mark>$1</mark>')
    }
  })
  return highlighted
}

const formatAnswer = (answer: string) => {
  // 简单的markdown格式转换
  return answer
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
}

const goToTutorial = (url: string) => {
  window.open(url, '_blank')
}
</script>

<style scoped>
.tutorial-search-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.search-input-section {
  margin-bottom: 30px;
}

.search-box {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.search-input {
  flex: 1;
}

.search-suggestions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.suggestion-tag {
  cursor: pointer;
}

.results-section {
  margin-top: 30px;
}

.mode-switch-hint {
  margin-bottom: 20px;
}

.results-header {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 20px;
  color: var(--el-text-color-primary);
}

.search-time {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.result-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 15px;
  transition: all 0.3s;
}

.result-card:hover {
  box-shadow: var(--el-box-shadow-light);
}

.result-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-color-primary);
  cursor: pointer;
  margin: 0 0 10px 0;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.relevance-score {
  color: var(--el-color-success);
  font-size: 14px;
}

.result-excerpt {
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin: 10px 0;
}

.qa-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
}

.confidence {
  margin-left: auto;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.qa-answer {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.answer-content {
  line-height: 1.8;
  margin-bottom: 20px;
}

.qa-sources {
  border-top: 1px solid var(--el-border-color);
  padding-top: 15px;
}

.source-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.source-relevance {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.qa-continue {
  margin-top: 20px;
}

.related-queries {
  margin-top: 30px;
}

.related-tag, .popular-tag {
  cursor: pointer;
  margin-right: 8px;
  margin-bottom: 8px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--el-text-color-secondary);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.welcome-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.quick-actions {
  margin-top: 30px;
}

.no-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

:deep(mark) {
  background-color: var(--el-color-warning-light-7);
  padding: 2px 4px;
  border-radius: 3px;
}
</style>
```

## 7. 手动模式选择

用户通过界面上的切换按钮手动选择搜索或问答模式，系统根据用户选择的模式执行相应的功能，不再进行自动判断。

## 8. 性能优化

### 8.1 缓存策略
```python
# 多级缓存
CACHE_STRATEGY = {
    "search_cache": {
        "ttl": 300,                    # 5分钟
        "max_size": 1000,              # 最大1000条
        "key_pattern": "search:{query_hash}:{mode}"
    },
    "qa_cache": {
        "ttl": 600,                    # 10分钟
        "max_size": 500,
        "key_pattern": "qa:{query_hash}"
    },
    "suggestion_cache": {
        "ttl": 1800,                   # 30分钟
        "max_size": 200,
        "key_pattern": "suggest:{prefix}"
    },
    "index_cache": {
        "ttl": 3600,                   # 1小时
        "preload": True                # 预加载热门索引
    }
}
```

### 8.2 异步处理
```python
# 异步处理流程
async def process_tutorial_async(resource_id: int):
    """异步处理教程内容"""
    try:
        # 1. 提取文本内容
        content = await extract_content(resource_id)
        
        # 2. 并行处理搜索和RAG索引
        search_task = asyncio.create_task(index_for_search(resource_id, content))
        rag_task = asyncio.create_task(index_for_rag(resource_id, content))
        
        # 3. 等待两个任务完成
        await asyncio.gather(search_task, rag_task)
        
        # 4. 更新状态
        await update_index_status(resource_id, completed=True)
        
    except Exception as e:
        await update_index_status(resource_id, completed=False, error=str(e))
```

## 9. 用户体验优化

### 9.1 智能提示
- **自动补全**: 基于历史搜索和热门查询
- **拼写纠错**: 自动纠正拼写错误
- **同义词扩展**: 自动扩展同义词
- **相关推荐**: 基于当前查询推荐相关内容

### 9.2 渐进式展示
```typescript
// 渐进式结果展示
interface ProgressiveResults {
  stage: 'understanding' | 'searching' | 'generating' | 'complete';
  progress: number;
  partialResults?: {
    searchPreview?: SearchResult[];
    answerPreview?: string;
    sourcesFound?: number;
  };
}
```

### 9.3 个性化体验
- **搜索历史**: 保存个人搜索历史
- **偏好学习**: 学习用户偏好，优化结果排序
- **智能推荐**: 基于历史行为推荐相关内容

## 10. 部署和监控

### 10.1 部署策略
```yaml
# docker-compose.yml
version: '3.8'
services:
  tutorial-search:
    build: .
    environment:
      - SEARCH_ENGINE=enabled
      - QA_ENGINE=enabled
      - CACHE_SIZE=1000
      - ASYNC_WORKERS=4
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - redis
      - postgres
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  monitoring:
    image: prometheus
    ports:
      - "9090:9090"
```

### 10.2 监控指标
```python
# 关键监控指标
METRICS = {
    "search_latency": Histogram("search_duration_seconds"),
    "qa_latency": Histogram("qa_duration_seconds"),
    "search_success_rate": Counter("search_success_total"),
    "qa_success_rate": Counter("qa_success_total"),
    "cache_hit_rate": Gauge("cache_hit_rate"),
    "user_satisfaction": Gauge("user_satisfaction_score"),
    "index_size": Gauge("tutorial_index_size"),
    "active_users": Gauge("active_users_count")
}
```

这个设计方案提供了一个**统一的搜索+AI问答界面**，用户可以通过一个输入框获得两种服务：
- **搜索模式**: 快速找到相关教程
- **问答模式**: 获得详细的AI解答
- **智能模式**: 系统自动选择最佳方式

系统会根据用户输入智能判断使用哪种模式，也可以手动切换，提供了最佳的用户体验。