import torch
from torch import nn
from src.audio2pose_models.cvae import CVAE
from src.audio2pose_models.discriminator import PoseSequenceDiscriminator
from src.audio2pose_models.audio_encoder import AudioEncoder

class Audio2Pose(nn.Module):
    def __init__(self, cfg, wav2lip_checkpoint, device='cuda'):
        super().__init__()
        self.cfg = cfg
        self.seq_len = cfg.MODEL.CVAE.SEQ_LEN
        self.latent_dim = cfg.MODEL.CVAE.LATENT_SIZE
        self.device = device

        self.audio_encoder = AudioEncoder(wav2lip_checkpoint, device)
        self.audio_encoder.eval()
        for param in self.audio_encoder.parameters():
            param.requires_grad = False

        self.netG = CVAE(cfg)
        self.netD_motion = PoseSequenceDiscriminator(cfg)
        
        
    def forward(self, x):

        batch = {}
        # 此处如果进行squeeze则会报shape不正确的错误 因为squeeze会去除一个维度的信息 但是如果不进行squeeze是否会导致训练结果与预期不符？
        # squeeze()是用于去除仅含有一条数据的维度 本质就是调整维度数量而不改变数据内容的一个函数
        coeff_gt = x['gt'].cuda()           #bs frame_len+1 73
        # coeff_gt = x['gt'].cuda().squeeze(0)           #bs frame_len+1 73

        batch['pose_motion_gt'] = coeff_gt[:, 1:, 64:70] - coeff_gt[:, :1, 64:70] #bs frame_len 6
        batch['ref'] = coeff_gt[:, 0, 64:70]  #bs  6  ##第一帧 参考帧
        # batch['class'] = x['class'].squeeze(0).cuda() # bs
        batch['class'] = x['class']
        indiv_mels= x['indiv_mels'].cuda().squeeze(0).unsqueeze(2) # bs seq_len+1 80 16

        # forward
        audio_emb_list = []
        # audio_emb = self.audio_encoder(indiv_mels[:, 1:, :, :].unsqueeze(2)) #bs seq_len 512
        audio_emb = self.audio_encoder(indiv_mels)
        batch['audio_emb'] = audio_emb
        batch = self.netG(batch)

        pose_motion_pred = batch['pose_motion_pred']           # bs frame_len 6
        pose_gt = coeff_gt[:, 1:, 64:70].clone()               # bs frame_len 6
        pose_pred = coeff_gt[:, :1, 64:70] + pose_motion_pred  # bs frame_len 6

        batch['pose_pred'] = pose_pred
        batch['pose_gt'] = pose_gt

        return batch

    def test(self, x):

        batch = {}
        ref = x['ref']                          #bs 1 70
        batch['ref'] = x['ref'][:,0,-6:]        #取第一帧的头部姿态
        batch['class'] = x['class']  
        bs = ref.shape[0]
        
        indiv_mels= x['indiv_mels']               # bs T 1 80 16
        indiv_mels_use = indiv_mels[:, 1:]        # we regard the ref as the first frame  忽略第一帧
        num_frames = x['num_frames']
        num_frames = int(num_frames) - 1

        #
        div = num_frames//self.seq_len
        re = num_frames%self.seq_len
        audio_emb_list = []
        pose_motion_pred_list = [torch.zeros(batch['ref'].unsqueeze(1).shape, dtype=batch['ref'].dtype, 
                                                device=batch['ref'].device)]  #第一帧的pose_motion就是pose_motion

        for i in range(div):
            z = torch.randn(bs, self.latent_dim).to(ref.device)  #latent
            batch['z'] = z
            audio_emb = self.audio_encoder(indiv_mels_use[:, i*self.seq_len:(i+1)*self.seq_len,:,:,:]) #bs seq_len 512
            batch['audio_emb'] = audio_emb
            batch = self.netG.test(batch)
            pose_motion_pred_list.append(batch['pose_motion_pred'])  #list of bs seq_len 6
        
        if re != 0:  #最后一个32长度
            z = torch.randn(bs, self.latent_dim).to(ref.device)
            batch['z'] = z
            audio_emb = self.audio_encoder(indiv_mels_use[:, -1*self.seq_len:,:,:,:]) #bs seq_len  512
            if audio_emb.shape[1] != self.seq_len:
                pad_dim = self.seq_len-audio_emb.shape[1]
                pad_audio_emb = audio_emb[:, :1].repeat(1, pad_dim, 1) 
                audio_emb = torch.cat([pad_audio_emb, audio_emb], 1) 
            batch['audio_emb'] = audio_emb
            batch = self.netG.test(batch)
            pose_motion_pred_list.append(batch['pose_motion_pred'][:,-1*re:,:])   
        
        pose_motion_pred = torch.cat(pose_motion_pred_list, dim = 1)
        batch['pose_motion_pred'] = pose_motion_pred

        pose_pred = ref[:, :1, -6:] + pose_motion_pred  # bs T 6  头部的残差

        batch['pose_pred'] = pose_pred
        return batch
