import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface ToastState {
  message: string;
  type: 'success' | 'error';
  visible: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private stateSubject = new BehaviorSubject<ToastState>({
    message: '',
    type: 'success',
    visible: false
  });

  toastState$ = this.stateSubject.asObservable();
  private timeoutId: any;

  show(message: string, type: 'success' | 'error' = 'success', duration: number = 3000) {
    // Clear existing timeout if a new toast comes in
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }

    // Show the toast
    this.stateSubject.next({ message, type, visible: true });

    // Hide it after 'duration' milliseconds
    this.timeoutId = setTimeout(() => {
      this.hide();
    }, duration);
  }

  hide() {
    const currentState = this.stateSubject.value;
    this.stateSubject.next({ ...currentState, visible: false });
  }
}