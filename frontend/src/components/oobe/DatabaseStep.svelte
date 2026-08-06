<script lang="ts">
import Icon from "@/components/common/Icon.svelte";
import { oobe } from "@/composables/oobe/useOobeWizard.svelte";
</script>

<div class="o-step-inner">
	<header class="o-step-head">
		<div class="o-step-tag">
			<Icon icon="material-symbols:storage-rounded" />
			Database & Cache
		</div>
		<h2 class="o-h2">数据库与缓存配置</h2>
		<p class="o-lead">选择适合你场景的数据库类型，Redis 为可选的高性能缓存层。</p>
	</header>

	<div class="o-db-select" role="radiogroup" aria-label="数据库类型">
		<label class="o-db-card" class:o-db-card-active={oobe.draft.database.dbType === "sqlite"}>
			<input type="radio" bind:group={oobe.draft.database.dbType} value="sqlite" aria-label="SQLite" />
			<div class="o-db-visual o-db-visual-sqlite" aria-hidden="true">
				<Icon icon="material-symbols:database-rounded" />
			</div>
			<div class="o-db-body">
				<div class="o-db-head">
					<h3 class="o-db-title">SQLite</h3>
					<span class="o-tag o-tag-recommended">
						<Icon icon="material-symbols:star-rounded" />
						新手推荐
					</span>
				</div>
				<p class="o-db-desc">
					零配置，首次启动自动在项目目录创建 <code>data/rosetta.db</code> 文件，最适合个人博客与小型站点。
				</p>
				<ul class="o-db-pros">
					<li><Icon icon="material-symbols:check-small-rounded" />无需独立服务</li>
					<li><Icon icon="material-symbols:check-small-rounded" />备份即复制单文件</li>
					<li><Icon icon="material-symbols:check-small-rounded" />性能满足日均 10w PV</li>
				</ul>
			</div>
		</label>

		<label class="o-db-card" class:o-db-card-active={oobe.draft.database.dbType === "postgres"}>
			<input type="radio" bind:group={oobe.draft.database.dbType} value="postgres" aria-label="PostgreSQL" />
			<div class="o-db-visual o-db-visual-pg" aria-hidden="true">
				<Icon icon="material-symbols:dns-rounded" />
			</div>
			<div class="o-db-body">
				<div class="o-db-head">
					<h3 class="o-db-title">PostgreSQL</h3>
				</div>
				<p class="o-db-desc">
					工业级关系型数据库，支持海量数据与高并发，适合生产环境与团队协作场景。
				</p>
				<ul class="o-db-pros">
					<li><Icon icon="material-symbols:check-small-rounded" />强大的查询能力</li>
					<li><Icon icon="material-symbols:check-small-rounded" />JSONB / 全文索引</li>
					<li><Icon icon="material-symbols:check-small-rounded" />适合横向扩展</li>
				</ul>
			</div>
		</label>
	</div>

	{#if oobe.draft.database.dbType === "postgres"}
		<div class="o-form-card">
			<div class="o-form-card-head">
				<Icon icon="material-symbols:tune-rounded" />
				<span>PostgreSQL 连接信息</span>
			</div>
			<div class="o-form-grid">
				<div class="o-field">
					<label for="db_host">
						<Icon icon="material-symbols:dns-rounded" class="o-label-icon" />
						主机地址
					</label>
					<input id="db_host" type="text" class:o-field-error={!!oobe.errors.dbHost} bind:value={oobe.draft.database.dbHost} placeholder="localhost" />
					{#if oobe.errors.dbHost}<p class="o-field-error" role="alert">{oobe.errors.dbHost}</p>{/if}
				</div>
				<div class="o-field">
					<label for="db_port">
						<Icon icon="material-symbols:router-rounded" class="o-label-icon" />
						端口
					</label>
					<input id="db_port" type="number" class:o-field-error={!!oobe.errors.dbPort} bind:value={oobe.draft.database.dbPort} placeholder="5432" />
					{#if oobe.errors.dbPort}<p class="o-field-error" role="alert">{oobe.errors.dbPort}</p>{/if}
				</div>
				<div class="o-field">
					<label for="db_name">
						<Icon icon="material-symbols:folder-open-rounded" class="o-label-icon" />
						数据库名
					</label>
					<input id="db_name" type="text" class:o-field-error={!!oobe.errors.dbName} bind:value={oobe.draft.database.dbName} placeholder="rosetta" />
					{#if oobe.errors.dbName}<p class="o-field-error" role="alert">{oobe.errors.dbName}</p>{/if}
				</div>
				<div class="o-field">
					<label for="db_user">
						<Icon icon="material-symbols:person-outline-rounded" class="o-label-icon" />
						用户名
					</label>
					<input id="db_user" type="text" class:o-field-error={!!oobe.errors.dbUser} bind:value={oobe.draft.database.dbUser} placeholder="postgres" />
					{#if oobe.errors.dbUser}<p class="o-field-error" role="alert">{oobe.errors.dbUser}</p>{/if}
				</div>
				<div class="o-field o-field-full">
					<label for="db_password">
						<Icon icon="material-symbols:lock-outline-rounded" class="o-label-icon" />
						密码
					</label>
					<input id="db_password" type="password" bind:value={oobe.draft.database.dbPassword} placeholder="••••••••" />
				</div>
			</div>
		</div>
	{:else}
		<div class="o-callout o-callout-info">
			<Icon icon="material-symbols:info-rounded" />
			<div class="o-callout-body">
				<strong>无需手动配置</strong>
				<p>安装过程将自动在项目根目录的 <code>data/</code> 下创建 <code>rosetta.db</code> 文件。</p>
			</div>
		</div>
	{/if}

	<div class="o-toggle-card" role="group" aria-label="Redis 缓存">
		<div class="o-toggle-head">
			<div class="o-toggle-icon-wrap o-toggle-icon-redis" aria-hidden="true">
				<Icon icon="material-symbols:bolt-rounded" />
			</div>
			<div class="o-toggle-text">
				<div class="o-toggle-title">启用 Redis 缓存</div>
				<p class="o-toggle-sub">显著提升高并发场景下的响应速度，生产环境建议开启。（可选）</p>
			</div>
			<button
				type="button"
				class="o-switch"
				class:o-switch-on={oobe.draft.database.redisEnable}
				role="switch"
				aria-checked={oobe.draft.database.redisEnable}
				on:click={() => (oobe.draft.database.redisEnable = !oobe.draft.database.redisEnable)}
				aria-label="启用 Redis 缓存"
			>
				<span class="o-switch-thumb"></span>
			</button>
		</div>

		{#if oobe.draft.database.redisEnable}
			<div class="o-form-grid o-form-inner">
				<div class="o-field">
					<label for="redis_host">
						<Icon icon="material-symbols:dns-rounded" class="o-label-icon" />
						Redis 主机
					</label>
					<input id="redis_host" type="text" bind:value={oobe.draft.database.redisHost} placeholder="localhost" />
				</div>
				<div class="o-field">
					<label for="redis_port">
						<Icon icon="material-symbols:router-rounded" class="o-label-icon" />
						端口
					</label>
					<input id="redis_port" type="number" bind:value={oobe.draft.database.redisPort} placeholder="6379" />
				</div>
				<div class="o-field o-field-full">
					<label for="redis_password">
						<Icon icon="material-symbols:lock-outline-rounded" class="o-label-icon" />
						密码（可选）
					</label>
					<input id="redis_password" type="password" bind:value={oobe.draft.database.redisPassword} placeholder="留空表示无密码" />
				</div>
			</div>
		{/if}
	</div>
</div>