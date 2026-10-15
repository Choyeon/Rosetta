/**
 * 填补 i18n 占位符：ja / zh_Hant 里存在形如 "[JA]:English source" / "[繁]:…" 的字面量，
 * 它们是批量生成时留下的占位，会原样渲染到前台（留言板、关于页、搜索页、动态流首当其冲）。
 *
 * 用法：node scripts/i18n_fill_placeholders.mjs          # 替换并打印剩余未映射项
 *       node scripts/i18n_fill_placeholders.mjs --check   # 只统计，不写文件
 *
 * 只改以 `[JA]:` / `[繁]:` 开头的字符串值，且仅当英文原句在表内命中；
 * 未命中的保留原样并打印出来，避免把没把握的句子编成机翻。
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const LOCALE_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../i18n/locales')
const CHECK_ONLY = process.argv.includes('--check')

/** [ 日本語, 繁體中文 ]，键为占位符里嵌的英文原句（含前导空格，逐字匹配） */
const MAP = {
  'just now': ['たった今', '剛剛'],
  ' min ago': [' 分前', ' 分鐘前'],
  ' h ago': [' 時間前', ' 小時前'],
  ' d ago': [' 天前', ' 天前'],
  'min ago': ['分前', '分鐘前'],
  'h ago': ['時間前', '小時前'],
  'd ago': ['天前', '天前'],
  'd ago ': ['天前', '天前'],

  'Settings': ['設定', '設定'],
  'Palette': ['カラーパレット', '配色'],
  'Choose a brand palette': ['ブランドカラーパレットを選択', '選擇品牌配色'],
  'Operation failed': ['操作に失敗しました', '操作失敗'],
  'Operation succeeded': ['操作に成功しました', '操作成功'],
  'Saved successfully': ['保存しました', '已儲存'],
  'Are you sure you want to delete? This cannot be undone.': ['削除してもよろしいですか？この操作は取り消せません。', '確定要刪除嗎？此操作無法復原。'],
  'Confirm Delete': ['削除の確認', '確認刪除'],
  'Publish': ['公開', '發布'],
  'Draft': ['下書き', '草稿'],
  'Search...': ['検索...', '搜尋...'],
  'No matching results found': ['該当する結果が見つかりません', '未找到相符結果'],
  'Loading...': ['読み込み中...', '載入中...'],
  'Loading…': ['読み込み中…', '載入中…'],
  'Upload': ['アップロード', '上傳'],
  'Select Image': ['画像を選択', '選擇圖片'],
  'Select category': ['カテゴリーを選択', '選擇分類'],
  'Newest first': ['新着順', '最新優先'],
  'Sort': ['並び替え', '排序'],
  'Most viewed': ['閲覧数順', '最多瀏覽'],
  'Nickname': ['ニックネーム', '暱稱'],
  'Email (kept private)': ['メール（非公開）', '電子郵件（不公開）'],
  'Website (optional)': ['ウェブサイト（任意）', '網站（選填）'],
  'Visit': ['アクセス', '前往'],
  'No description': ['説明なし', '暫無描述'],
  'No matches found': ['該当する結果がありません', '未找到匹配內容'],
  'No matching posts': ['該当する記事がありません', '沒有相符文章'],
  'No matching results': ['該当する結果がありません', '未找到相符結果'],
  'Try a different keyword, or clear the filters.': ['別のキーワードで試すか、フィルターをクリアしてください。', '換個關鍵詞，或清除篩選看看。'],
  'Clear filters': ['フィルターをクリア', '清除篩選'],
  'Filter': ['フィルター', '篩選'],
  'Home': ['ホーム', '首頁'],
  'Posts': ['記事', '文章'],
  'Categories': ['カテゴリー', '分類'],
  'All Tags': ['すべてのタグ', '所有標籤'],
  'All categories': ['すべてのカテゴリー', '所有分類'],
  'All posts': ['すべての記事', '全部文章'],
  'Browse posts': ['記事を一覧', '瀏覽文章'],
  'Browse content by topic': ['テーマ別にコンテンツを閲覧', '依主題瀏覽內容'],
  'Browse everything published, organized by date': ['公開済みの記事を日付順に閲覧', '依日期瀏覽所有已發布內容'],
  'No archived posts yet': ['アーカイブされた記事はまだありません', '尚無歸檔文章'],
  'No categories yet': ['カテゴリーはまだありません', '尚無分類'],
  'No tags yet': ['タグはまだありません', '尚無標籤'],
  'No posts yet': ['まだ記事がありません', '尚無文章'],
  'posts': ['記事', '篇'],
  'photos': [' 枚', ' 張'],
  'words': ['字', '字'],
  'chars': ['文字', '字元'],
  'min read': [' 分で読了', ' 分鐘阅读'],
  'Untitled Post': ['無題の記事', '未命名文章'],
  'No excerpt available': ['抜粋はありません', '暫無摘要'],
  'Write a comment…': ['コメントを書く…', '撰寫評論…'],
  'Submitting…': ['送信中…', '提交中…'],
  'Submit failed, please try again later': ['送信に失敗しました。後ほど再度お試しください', '提交失敗，請稍後重試'],
  'Post Comment': ['コメントを投稿', '發表評論'],
  'No comments yet. Leave the first word.': ['まだコメントがありません。最初の一言をどうぞ。', '還沒有評論，來寫下第一句吧。'],
  'Sign in to engage': ['ログインして参加', '登入後參與'],
  'Please sign in before posting a comment.': ['コメントを投稿するには先にログインしてください。', '發表評論前請先登入。'],
  'Go to login': ['ログインへ', '前往登入'],
  'Go to Login': ['ログインへ', '前往登入'],
  'Crossing the boundaries of language': ['言語の壁を越えて', '跨越語言的邊界'],
  'Open Beta — Join Today': ['オープンβ — 今日参加しよう', '公開測試 — 即刻加入'],
  'Re-enter your password': ['パスワードを再入力', '再次輸入密碼'],
  'I have read and agree to the': ['読んだ上で次に同意します：', '我已閱讀並同意'],
  'By registering, you agree to our Terms of Service and Privacy Policy': ['登録すると、利用規約とプライバシーポリシーに同意したことになります', '註冊即表示你同意我們的服務條款與隱私政策'],
  'Join the Rosetta Community': ['Rosetta コミュニティに参加', '加入 Rosetta 社群'],
  'Multilingual content. One home.': ['多言語のコンテンツ、ひとつの場所。', '多語內容，同一個家。'],
  'Write your story alongside thousands of creators': ['何千ものクリエイターとともに、あなたの物語を。', '與上千位創作者一起寫下你的故事'],
  'Minimal Writing': ['ミニマルな執筆', '極簡寫作'],
  'Focus on content, not a clunky editor': ['編集操作ではなく、内容に集中', '專注內容，而非笨重的編輯器'],
  'Multi-language': ['多言語対応', '多語系'],
  'Built-in i18n for a global audience': ['国際化を内蔵、世界中の読者へ', '內建多語系，面向全球讀者'],
  'High Performance': ['高いパフォーマンス', '高效能'],
  'Modern architecture with blazing fast loads': ['モダンなアーキテクチャで、驚くほど速い表示', '現代架構，載入飛快'],
  'All rights reserved': ['無断転載を禁じます', '版權所有'],
  'Terms of Service': ['利用規約', '服務條款'],
  'and': ['および', '及'],
  'Privacy Policy': ['プライバシーポリシー', '隱私政策'],
  'Registering...': ['登録中...', '註冊中...'],
  'Create Account': ['アカウント作成', '建立帳號'],
  'Passwords do not match': ['パスワードが一致しません', '兩次輸入的密碼不一致'],
  'Registration failed, please try again later': ['登録に失敗しました。時間をおいて再度お試しください', '註冊失敗，請稍後重試'],
  'Switch wallpaper': ['壁紙を切り替え', '更換壁紙'],
  'Start Writing': ['書き始める', '開始寫作'],
  'Hot Ranking': ['ホットランキング', '熱門榜'],
  'HN-style composite score weighted by upvotes, views, comments and freshness.': ['高評価・閲覧・コメント・鮮度を加重した HN 風の総合スコア。', '由點讚、瀏覽、評論與新鮮度加權的 HN 風格綜合分數。'],
  'Everything published, in reverse chronological order.': ['公開済みの記事を新しい順に並べます。', '已發布文章依時間倒序排列。'],
  'The author is cooking up new content — check back soon.': ['書き手が新しい内容を準備中です — また後ほどどうぞ。', '作者正在醞釀新內容 — 敬請期待。'],

  'Activity': ['アクティビティ', '動態'],
  'A pulse of this little site — new posts, comments, shares.': ['この小さなサイトの鼓動 — 新記事、コメント、共有。', '這個站點的脈動 — 新文章、評論與分享。'],
  'New Post': ['新記事', '新文章'],
  'New Card': ['新カード', '新卡片'],
  'New Comment': ['新コメント', '新評論'],
  'Like': ['いいね', '喜歡'],
  'Thought': ['つぶやき', '碎碎念'],
  'Article Update': ['記事の更新', '文章更新'],
  'Site Update': ['サイト更新', '網站更新'],
  'Announcement': ['お知らせ', '公告'],
  'Link Share': ['リンク共有', '連結分享'],
  'liked the post': ['が記事をいいねしました', '讚了這篇文章'],
  'No activity yet': ['まだ動きがありません', '暫無動態'],

  'About': ['このサイトについて', '關於'],
  'About the author behind this site, the tech stack, and everything.': ['このサイトを運営する筆者と、技術スタック、あれこれについて。', '關於站點背後的作者、技術棧與一切。'],
  'Rosetta': ['Rosetta', 'Rosetta'],
  'Indie Developer · Blogger': ['インディー開発者 · ブロガー', '獨立開發者 · 部落格作者'],
  'Full-stack Engineer': ['フルスタックエンジニア', '全端工程師'],
  'Open Source Lover': ['オープンソース愛好者', '開源愛好者'],
  'Photography Hobbyist': ['写真愛好家', '攝影愛好者'],
  'Coffee-driven': ['コーヒーで駆動', '咖啡驅動'],
  'Bio': ['紹介', '簡介'],
  'Skills': ['スキル', '技能'],
  'Open Source': ['オープンソース', '開源'],
  'Contact': ['お問い合わせ', '聯絡方式'],
  'Motto': ['座右の銘', '座右銘'],
  'Tech Stack': ['技術スタック', '技術棧'],
  'Core technologies and tools powering this site and my daily work': ['このサイトと日常の仕事を支える主要技術とツール', '支撐這個站點與日常開發的核心技術與工具'],
  'Stay hungry, stay foolish. Write code, write life.': ['ハングリーであれ、愚かであれ。コードを書き、人生を書く。', '保持飢渴，保持愚蠢。寫代碼，也寫生活。'],
  'Hi, I\'m the maintainer behind Rosetta. I write product code by day, hack on open-source projects by night, and wander around with a camera on weekends. This blog is where I keep engineering notes, reading notes, and bits of life — a simple place for thoughts to leave footprints.': ['こんにちは。Rosetta を運営しています。昼は製品コードを書き、夜はオープンソースに触れ、週末はカメラを持って街を歩きます。このブログには開発の備忘録、読書の記録、生活の断片を置いていきます — 考えが足跡を残す、シンプルな場所として。', '你好，我是 Rosetta 背後維護者。白天寫產品程式碼，晚上玩開源，週末帶著相機四處走。這個部落格記錄工程筆記、閱讀隨想與生活碎片 — 一個讓思考留下足跡的簡單地方。'],
  'My focus is mainly on Web frontend architecture, developer experience, and toolchains that just feel good to use. Minimalism is my taste — I seek balance through restraint, both in code and in design.': ['関心領域は Web フロントエンドのアーキテクチャ、開発者体験、そして心地よく使えるツールチェーン。ミニマリズムが好みで、コードにもデザインにも、引き算による均衡を求めます。', '我主要關注 Web 前端架構、開發者體驗，以及用起來順手的工具鏈。極簡是我的口味 — 無論寫程式還是做設計，都在克制中尋找平衡。'],
  'If anything here resonates with you, feel free to drop a note in the guestbook, or reach out via email or social links below. Link exchanges are always welcome — let\'s keep the indie web woven together.': ['もし共感してくれたなら、掲示板にひとことどうぞ。メールや下の SNS からも連絡できます。相互リンクはいつでも歓迎です — インディー Web をもっと密に織りいきましょう。', '如果這裡有內容讓你產生共鳴，歡迎到留言板留一句，或透過郵件與下方的社群連結聯絡我。交換連結永遠歡迎 — 讓我們一起把獨立網路編織得更緊一些。'],
  'Buy Me a Coffee': ['コーヒーをおごる', '請我喝杯咖啡'],
  'If any article or code here helped you, consider supporting me through the links below. A like, comment, or share is already the best coffee I could ask for.': ['記事やコードが役立ったなら、下のリンクから応援していただけると嬉しいです。いいね・コメント・共有だけでも、これ以上ないほど励ましになります。', '如果這裡的文章或程式碼幫到了你，可以透過下方連結支持我。哪怕只是一個讚、一句評論或一次分享，就已經是最好的咖啡了。'],

  'Guestbook': ['掲示板', '留言板'],
  'Leave a note, drop a footprint. Every voice is carefully read.': ['ひとこと残して、足跡を残して。すべての声を大切に読んでいます。', '留一句話，留下一個足跡。每一條留言都會認真讀。'],
  'No messages yet. Be the first to say hi!': ['まだメッセージがありません。最初のひとことをどうぞ！', '還沒有留言。來當第一個打招呼的人吧！'],
  'Reply to this message…': ['このメッセージに返信…', '回覆這條留言…'],
  'Write a message': ['メッセージを書く', '寫留言'],

  'Friends': ['相互リンク', '友情連結'],
  'Wonderful folks and their sites, worth sharing with more readers.': ['素晴らしい仲間とそのサイト — もっと多くの読者に届けたい。', '厲害的夥伴和他們的站點，值得分享給更多讀者。'],
  'No friend links yet': ['相互リンクはまだありません', '尚無友情連結'],

  'Gallery': ['ギャラリー', '相簿'],
  'No albums yet': ['アルバムはまだありません', '尚無相簿'],
  'Travels, daily life, light and shadow. Slices of time frozen through the lens.': ['旅、日常、光と影。レンズに切り取った時間の断片。', '旅行、日常、光與影。鏡頭凍結的時間切片。'],
  '{count} photos · sorted by {sortOrder}': ['{count} 枚 · {sortOrder} 順', '共 {count} 張照片 · 按 {sortOrder} 排序'],
  'Explore tags to find related content. Larger tiles mean more posts.': ['タグから関連コンテンツを探せます。タイルが大きいほど記事数が多いです。', '透過標籤探索相關內容，磁磚越大代表文章越多。'],

  'Search': ['検索', '搜尋'],
  'Search titles or keywords…': ['タイトルやキーワードを検索…', '搜尋標題或關鍵詞…'],
  'Type something here…': ['ここに入力…', '在此輸入…'],
  'Type keywords and press Enter or click Search…': ['キーワードを入力して Enter、または「検索」をクリック…', '輸入關鍵詞後按 Enter 或點擊搜尋…'],
  'Start searching': ['検索を始める', '開始搜尋'],
  'Enter keywords above to search across titles, bodies, tags and categories.': ['上でキーワードを入力すると、タイトル・本文・タグ・カテゴリーを検索できます。', '在上方輸入關鍵詞，支援標題、正文、標籤和分類全文檢索。'],
  'Find articles by title, content, tags or categories — full-text at your fingertips.': ['タイトル・内容・タグ・カテゴリーから記事を探せます — フルテキスト検索を指先に。', '從標題、內容、標籤、分類中快速找到你想看的文章。'],
  'Found {count} result(s) related to': ['関連する結果を {count} 件発見', '找到 {count} 條相關結果'],

  // 键里要带反斜杠：脚本按文件原文匹配，原文的引号是 \" 两个字符。
  'Found {count} result(s) related to \\"{keyword}\\"': ['「{keyword}」関連の結果 {count} 件', '找到 {count} 條與「{keyword}」相關的結果'],
  'No articles contain \\"{keyword}\\". Try another keyword or clear the search to see everything.': ['「{keyword}」を含む記事が見つかりません。キーワードを変えるか、検索をクリアして全体をご覧ください。', '沒有包含「{keyword}」的文章，試試換一個關鍵詞，或者清除搜尋查看全部。'],
  '共 {count} 張照片 · 按 {sortOrder} 排序': ['{count} 枚 · {sortOrder} 順', '共 {count} 張照片 · 按 {sortOrder} 排序'],
  '在上方輸入關鍵詞，支援標題、正文、標籤和分類全文檢索。': ['上でキーワードを入力すると、タイトル・本文・タグ・カテゴリーを検索できます。', '在上方輸入關鍵詞，支援標題、正文、標籤和分類全文檢索。'],
  '從標題、內容、標籤、分類中快速找到你想看的文章。': ['タイトル・内容・タグ・カテゴリーから記事を探せます。', '從標題、內容、標籤、分類中快速找到你想看的文章。'],
  '找到 {count} 條與「{keyword}」相關的結果': ['「{keyword}」関連の結果 {count} 件', '找到 {count} 條與「{keyword}」相關的結果'],
  '搜尋': ['検索', '搜尋'],
  '沒有包含「{keyword}」的文章，試試換一個關鍵詞，或者清除搜尋查看全部。': ['「{keyword}」を含む記事が見つかりません。キーワードを変えるか、検索をクリアして全体をご覧ください。', '沒有包含「{keyword}」的文章，試試換一個關鍵詞，或者清除搜尋查看全部。'],
  '沒有找到匹配的內容': ['該当するコンテンツがありません', '沒有找到匹配的內容'],
  '輸入關鍵詞，按回車或點擊搜尋…': ['キーワードを入力して Enter、または「検索」をクリック…', '輸入關鍵詞，按回車或點擊搜尋…'],
  '開始搜尋': ['検索を始める', '開始搜尋']
}

function transform(text, slot) {
  let filled = 0
  let missed = 0
  // 值里可能含转义引号（如 「{keyword}」的 \" 包裹），所以按 (?:[^"\\]|\\.)* 整段取。
  const out = text.replace(/"(\[JA\]:|\[繁\]:)((?:[^"\\]|\\.)*)"/g, (raw, prefix, body) => {
    const entry = MAP[body]
    if (!entry) {
      missed++
      return raw
    }
    filled++
    return `"${entry[slot]}"`
  })
  return { out, filled, missed }
}

const files = [['ja.json', 0], ['zh_Hant.json', 1]]
for (const [file, slot] of files) {
  const path = resolve(LOCALE_DIR, file)
  const src = readFileSync(path, 'utf8')
  const { out, filled, missed } = transform(src, slot)
  if (!CHECK_ONLY && filled > 0) writeFileSync(path, out, 'utf8')
  console.log(`${file}: filled=${filled} stillPlaceholder=${missed}`)
}
