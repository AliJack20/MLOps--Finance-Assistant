import { Component, OnInit } from '@angular/core';
import { ToastService, ToastState } from '../../services/toast.service';

@Component({
  selector: 'app-toast',
  standalone: false,
  templateUrl: './toast.component.html',
  styleUrls: ['./toast.component.css']
})
export class ToastComponent implements OnInit {
  state: ToastState = { message: '', type: 'success', visible: false };

  constructor(private toastService: ToastService) {}

  ngOnInit() {
    this.toastService.toastState$.subscribe(state => {
      this.state = state;
    });
  }
}