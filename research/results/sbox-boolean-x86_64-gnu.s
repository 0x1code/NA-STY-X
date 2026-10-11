_RNvCs9jCRKZx87Uq_13nastyx_engine14round_function:
.seh_proc _RNvCs9jCRKZx87Uq_13nastyx_engine14round_function
	pushq	%rsi
	.seh_pushreg %rsi
	pushq	%rdi
	.seh_pushreg %rdi
	pushq	%rbx
	.seh_pushreg %rbx
	subq	$2144, %rsp
	.seh_stackalloc 2144
	.seh_endprologue
	movq	%rdx, %rsi
	movabsq	$72340172838076673, %rdi
	xorq	%rdx, %rcx
	movq	%rcx, %rax
	andq	%rdi, %rax
	movq	%rcx, %rdx
	shrq	%rdx
	andq	%rdi, %rdx
	movq	%rcx, %r8
	shrq	$2, %r8
	andq	%rdi, %r8
	movq	%rcx, %r9
	shrq	$3, %r9
	andq	%rdi, %r9
	movq	%rcx, %r10
	shrq	$4, %r10
	andq	%rdi, %r10
	movq	%rcx, %r11
	shrq	$5, %r11
	andq	%rdi, %r11
	movq	%rcx, %rbx
	shrq	$6, %rbx
	andq	%rdi, %rbx
	shrq	$7, %rcx
	andq	%rdi, %rcx
	movq	%rax, 32(%rsp)
	movq	%rdx, 40(%rsp)
	movq	%r8, 48(%rsp)
	movq	%r9, 56(%rsp)
	movq	%r10, 64(%rsp)
	movq	%r11, 72(%rsp)
	movq	%rbx, 80(%rsp)
	movq	%rcx, 88(%rsp)
	leaq	104(%rsp), %rcx
	movl	$2040, %r8d
	xorl	%edx, %edx
	callq	memset
	movq	%rdi, 96(%rsp)
	movl	$1, %ecx
	movabsq	$-4702111234474983746, %rax
	leaq	.Lanon.0dade3a9f0335b813f7e21fbefd792c9.0(%rip), %rdx
	.p2align	4
.LBB0_1:
	rep		bsfq	%rcx, %r8
	leaq	-1(%rcx), %r9
	andq	%rcx, %r9
	movq	32(%rsp,%r8,8), %r8
	andq	96(%rsp,%r9,8), %r8
	movq	%r8, 96(%rsp,%rcx,8)
	movzbl	(%rcx,%rdx), %r9d
	movq	%r8, %r10
	shlq	$8, %r10
	subq	%r8, %r10
	imulq	%rdi, %r9
	andq	%r10, %r9
	xorq	%r9, %rax
	incq	%rcx
	cmpq	$256, %rcx
	jne	.LBB0_1
	movl	%eax, %ecx
	shrl	$16, %ecx
	movq	%rax, %rdx
	shlq	$32, %rdx
	movabsq	$-72057594037927936, %r8
	andq	%rdx, %r8
	movabsq	$71776119061217280, %r9
	andq	%rax, %r9
	orq	%r8, %r9
	movabsq	$280375465082880, %r8
	andq	%rdx, %r8
	orq	%r9, %r8
	movabsq	$1095216660480, %rdx
	andq	%rax, %rdx
	orq	%r8, %rdx
	movq	%rax, %r8
	shrq	$32, %r8
	movl	%r8d, %r9d
	andl	$-16777216, %r9d
	orq	%rdx, %r9
	movzbl	%al, %eax
	shll	$16, %eax
	orq	%r9, %rax
	andl	$65280, %r8d
	orq	%rax, %r8
	movzbl	%cl, %eax
	orq	%r8, %rax
	movq	%rax, %rcx
	rolq	$17, %rcx
	addq	%rax, %rcx
	rolq	$41, %rax
	xorq	%rcx, %rax
	movq	%rax, %rcx
	rolq	$31, %rcx
	addq	%rax, %rcx
	rolq	$23, %rax
	xorq	%rcx, %rax
	movq	%rax, %rcx
	rolq	$11, %rcx
	addq	%rax, %rcx
	rolq	$37, %rax
	xorq	%rsi, %rax
	xorq	%rcx, %rax
	.seh_startepilogue
	addq	$2144, %rsp
	popq	%rbx
	popq	%rdi
	popq	%rsi
	.seh_endepilogue
	retq
	.seh_endproc
