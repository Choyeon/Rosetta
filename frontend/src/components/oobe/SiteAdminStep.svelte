<script lang="ts">
import Icon from "@/components/common/Icon.svelte";
import { oobe } from "@/composables/oobe/useOobeWizard.svelte";
</script>

<div class="o-step-inner">
	<header class="o-step-head">
		<div class="o-step-tag">
			<Icon icon="material-symbols:manage-accounts-rounded" />
			Site & Administrator
		</div>
		<h2 class="o-h2">站点信息与管理员</h2>
		<p class="o-lead">配置你的站点基础信息，以及首个拥有全部权限的管理员账户。</p>
	</header>

	<div class="o-cols">
		<div class="o-col">
			<div class="o-col-head">
				<div class="o-col-icon o-col-icon-cyan" aria-hidden="true">
					<Icon icon="material-symbols:home-rounded" />
				</div>
				<div>
					<h3 class="o-col-title">站点信息</h3>
					<p class="o-col-sub">安装完成后可在后台随时修改</p>
				</div>
			</div>
			<div class="o-col-body">
				<div class="o-field">
					<label for="site_name">
						<Icon icon="material-symbols:label-important-rounded" class="o-label-icon" />
						站点名称 <span class="o-req">*</span>
					</label>
					<input
						id="site_name"
						type="text"
						class:o-field-error={!!oobe.errors.siteName}
						aria-invalid={!!oobe.errors.siteName}
						bind:value={oobe.draft.site.siteName}
						on:blur={() => !oobe.draft.site.siteName.trim() ? (oobe.errors = { ...oobe.errors, siteName: "请输入站点名称" }) : (() => { const n = { ...oobe.errors }; delete n.siteName; oobe.errors = n; })()}
						placeholder="例如：Rosetta 的自留地"
					/>
					{#if oobe.errors.siteName}<p class="o-field-error" role="alert">{oobe.errors.siteName}</p>{/if}
				</div>
				<div class="o-field">
					<label for="site_url">
						<Icon icon="material-symbols:link-rounded" class="o-label-icon" />
						站点 URL
					</label>
					<input id="site_url" type="text" bind:value={oobe.draft.site.siteUrl} placeholder="https://example.com" />
				</div>
				<div class="o-field">
					<label for="site_description">
						<Icon icon="material-symbols:article-shortcut-rounded" class="o-label-icon" />
						站点描述
					</label>
					<input id="site_description" type="text" bind:value={oobe.draft.site.siteDescription} placeholder="一句话介绍你的站点" />
				</div>
				<div class="o-field">
					<label for="site_keywords">
						<Icon icon="material-symbols:sell-rounded" class="o-label-icon" />
						关键词（英文逗号分隔）
					</label>
					<input id="site_keywords" type="text" bind:value={oobe.draft.site.siteKeywords} placeholder="博客, 技术, 生活" />
				</div>
				<div class="o-field">
					<label for="site_author">
						<Icon icon="material-symbols:draw-outline-rounded" class="o-label-icon" />
						作者昵称
					</label>
					<input id="site_author" type="text" bind:value={oobe.draft.site.siteAuthor} placeholder="Admin" />
				</div>
				<div class="o-field">
					<label for="site_email">
						<Icon icon="material-symbols:mail-outline-rounded" class="o-label-icon" />
						联系邮箱
					</label>
					<input id="site_email" type="email" bind:value={oobe.draft.site.siteEmail} placeholder="admin@example.com" />
				</div>
			</div>
		</div>

		<div class="o-col">
			<div class="o-col-head">
				<div class="o-col-icon o-col-icon-violet" aria-hidden="true">
					<Icon icon="material-symbols:shield-person-rounded" />
				</div>
				<div>
					<h3 class="o-col-title">管理员账户</h3>
					<p class="o-col-sub">首个账户默认拥有全部权限</p>
				</div>
			</div>
			<div class="o-col-body">
				<div class="o-field">
					<label for="admin_username">
						<Icon icon="material-symbols:person-outline-rounded" class="o-label-icon" />
						用户名 <span class="o-req">*</span>
					</label>
					<input
						id="admin_username"
						type="text"
						class:o-field-error={!!oobe.errors.adminUsername}
						aria-invalid={!!oobe.errors.adminUsername}
						bind:value={oobe.draft.admin.adminUsername}
						on:blur={() => oobe.validateAdminUsername()}
						placeholder="3-20 位字母、数字、下划线或短横线"
					/>
					{#if oobe.errors.adminUsername}<p class="o-field-error" role="alert">{oobe.errors.adminUsername}</p>{/if}
				</div>
				<div class="o-field">
					<label for="admin_email">
						<Icon icon="material-symbols:mail-outline-rounded" class="o-label-icon" />
						邮箱 <span class="o-req">*</span>
					</label>
					<input
						id="admin_email"
						type="email"
						class:o-field-error={!!oobe.errors.adminEmail}
						aria-invalid={!!oobe.errors.adminEmail}
						bind:value={oobe.draft.admin.adminEmail}
						on:blur={() => oobe.validateAdminEmail()}
						placeholder="admin@example.com"
					/>
					{#if oobe.errors.adminEmail}<p class="o-field-error" role="alert">{oobe.errors.adminEmail}</p>{/if}
				</div>
				<div class="o-field">
					<label for="admin_nickname">
						<Icon icon="material-symbols:badge-outline-rounded" class="o-label-icon" />
						显示昵称
					</label>
					<input id="admin_nickname" type="text" bind:value={oobe.draft.admin.adminNickname} placeholder="文章作者显示名" />
				</div>
				<div class="o-field">
					<label for="admin_password">
						<Icon icon="material-symbols:lock-outline-rounded" class="o-label-icon" />
						密码 <span class="o-req">*</span>
					</label>
					<input
						id="admin_password"
						type="password"
						class:o-field-error={!!oobe.errors.adminPassword}
						aria-invalid={!!oobe.errors.adminPassword}
						bind:value={oobe.draft.admin.adminPassword}
						on:blur={() => oobe.validateAdminPwd()}
						placeholder="至少 8 位，建议包含大小写字母和数字"
					/>
					<p class="o-field-hint">
						<Icon icon="material-symbols:shield-outline-rounded" />
						建议至少包含大小写字母、数字和特殊符号中的三类
					</p>
					{#if oobe.errors.adminPassword}<p class="o-field-error" role="alert">{oobe.errors.adminPassword}</p>{/if}
				</div>
				<div class="o-field">
					<label for="confirm_admin_password">
						<Icon icon="material-symbols:enhanced-encryption-rounded" class="o-label-icon" />
						确认密码 <span class="o-req">*</span>
					</label>
					<input
						id="confirm_admin_password"
						type="password"
						class:o-field-error={!!oobe.errors.confirmAdminPassword}
						aria-invalid={!!oobe.errors.confirmAdminPassword}
						bind:value={oobe.draft.admin.confirmAdminPassword}
						on:blur={() => oobe.validateAdminConfirm()}
						placeholder="请再次输入相同的密码"
					/>
					{#if oobe.errors.confirmAdminPassword}<p class="o-field-error" role="alert">{oobe.errors.confirmAdminPassword}</p>{/if}
				</div>
			</div>
		</div>
	</div>
</div>