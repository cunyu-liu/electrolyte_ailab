module load conda
conda activate qwen_finetune


2.1 软件安装&环境变量
软件安装目录：/opt/gengzi/pub/softwares
服务器通过module管理环境变量，常用命令如下：

module avail # 查看已有环境变量(软件)
module load XXX # 加载环境变量(软件)，XXX为具体需要加载的环境变量名
module load LAMMPS # e.g., 加载LAMMPS，将自动加载默认LAMMPS版本
module load LAMMPS/3Nov2022 # 加载LAMMPS的3Nov2022版本
module # 查看module详细命令

2.2 任务提交
提交脚本和相关命令同e5，可参照E5系统使用说明中的(三)slurm作业管理软件的使用
提交脚本示例目录：/home/sub_scripts
slrum常用命令如下：
命令 功能 使用
sinfo 显示系统资源使用情况 执行sinfo
STATE:idle 表示空闲
STATE:alloc表示占用
STATE:down表示离线
squeue 显示作业状态 squeue
JOBID为任务号
NAME为任务名
USER为用户名
ST:PD为排队中
ST:R为运行中
TIME为已运行时间
NODES为节点数
NODELIST为使用节点名或排队状态
sbatch 用于批处理作业提交 sbatch job.sh
scancel 用于取消已提交的作业 scancel JOBID
scancel -u username删除所有任务
scontrol 查询节点信息或正在运行的作业信息 scontrol show jobid JOBID
srun -h 查看slurm详细命令

2.3 节点配置
1个48核的登录节点：master
30个64核的cpu计算节点：cn1-cn30
1个52核8卡的gpu计算节点：gpu1

2.4 机时使用情况查询
sreport命令 https://slurm.schedmd.com/sreport.html


