_RNvCs7i4ZeRrVc6P_12memory_probe7destroy:
	cmpl	$7, (%rcx)
	je	.LBB6_2
	movq	$0, 8(%rcx)
	#MEMBARRIER
	movq	$0, 16(%rcx)
	#MEMBARRIER
	movq	$0, 24(%rcx)
	#MEMBARRIER
	movq	$0, 32(%rcx)
	#MEMBARRIER
	movq	$0, 40(%rcx)
	#MEMBARRIER
	movq	$0, 48(%rcx)
	#MEMBARRIER
	movq	$0, 56(%rcx)
	#MEMBARRIER
	movq	$0, 64(%rcx)
	#MEMBARRIER
	movq	$0, 72(%rcx)
	#MEMBARRIER
	movq	$0, 80(%rcx)
	#MEMBARRIER
	movq	$0, 88(%rcx)
	#MEMBARRIER
	movq	$0, 96(%rcx)
	#MEMBARRIER
	movq	$0, 104(%rcx)
	#MEMBARRIER
	movq	$0, 112(%rcx)
	#MEMBARRIER
	movq	$0, 120(%rcx)
	#MEMBARRIER
	movq	$0, 128(%rcx)
	#MEMBARRIER
	movq	$0, 136(%rcx)
	#MEMBARRIER
	movq	$0, 144(%rcx)
	#MEMBARRIER
	movq	$0, 152(%rcx)
	#MEMBARRIER
	movq	$0, 160(%rcx)
	#MEMBARRIER
	movq	$0, 168(%rcx)
	#MEMBARRIER
	movq	$0, 176(%rcx)
	#MEMBARRIER
	movq	$0, 184(%rcx)
	#MEMBARRIER
	movq	$0, 192(%rcx)
	#MEMBARRIER
.LBB6_2:
	movq	$7, (%rcx)
	retq
