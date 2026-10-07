<script setup>
// Cadre commun des questionnaires guidés de l'assistant : titre, étapes numérotées, corps et pied de carte.
defineProps({
	title: { type: String, required: true },
	subtitle: { type: String, default: "" },
	steps: { type: Array, default: () => [] }, // libellés des étapes
	step: { type: Number, default: 1 }, // étape courante (1…n)
	error: { type: String, default: "" },
});
</script>

<template>
	<section class="fs-card" :aria-label="title">
		<div class="fs-head">
			<div>
				<h3 class="fs-title">{{ title }}</h3>
				<p v-if="subtitle" class="fs-sub">{{ subtitle }}</p>
			</div>
			<ol v-if="steps.length" class="fs-steps" aria-label="Étapes">
				<li v-for="(label, i) in steps" :key="label" :class="{ done: i + 1 < step, on: i + 1 === step }" :aria-current="i + 1 === step ? 'step' : undefined">
					<span class="fs-dot">{{ i + 1 < step ? "✓" : i + 1 }}</span>
					<span class="fs-label">{{ label }}</span>
				</li>
			</ol>
		</div>
		<div class="fs-body"><slot /></div>
		<p v-if="error" class="fs-error" role="alert">{{ error }}</p>
		<div class="fs-foot"><slot name="footer" /></div>
	</section>
</template>

<style scoped>
.fs-card {
	width: 100%;
	padding: 18px 20px;
	border: 1px solid #e0dfda;
	border-radius: 16px;
	background: #fff;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
	animation: fs-in 0.28s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
@keyframes fs-in {
	from {
		opacity: 0;
		transform: translateY(8px);
	}
	to {
		opacity: 1;
		transform: none;
	}
}
.fs-head {
	display: flex;
	flex-wrap: wrap;
	align-items: flex-start;
	justify-content: space-between;
	gap: 10px 20px;
	margin-bottom: 14px;
}
.fs-title {
	margin: 0;
	font-size: 15px;
	font-weight: 650;
	color: #09090b;
}
.fs-sub {
	margin: 3px 0 0;
	font-size: 12.5px;
	color: #6b6a66;
}
.fs-steps {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 14px;
	margin: 0;
	padding: 0;
	list-style: none;
}
.fs-steps li {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 12px;
	color: #6b6a66;
}
.fs-dot {
	display: grid;
	place-items: center;
	width: 20px;
	height: 20px;
	border-radius: 50%;
	background: #ecebe6;
	font-size: 11px;
	font-weight: 600;
	color: #55544f;
	transition: background-color 0.2s ease, color 0.2s ease;
}
.fs-steps li.on {
	color: #09090b;
	font-weight: 600;
}
.fs-steps li.on .fs-dot {
	background: #047857;
	color: #fff;
}
.fs-steps li.done .fs-dot {
	background: #d8f0e4;
	color: #066336;
}
.fs-error {
	margin: 12px 0 0;
	padding: 9px 12px;
	border-radius: 10px;
	background: #fbeaea;
	color: #b42318;
	font-size: 13px;
}
.fs-foot {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-top: 16px;
	padding-top: 14px;
	border-top: 1px solid #efeeea;
}
.fs-foot:empty {
	display: none;
}
@media (prefers-reduced-motion: reduce) {
	.fs-card {
		animation: none;
	}
}
</style>
